#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
OVH CLI. This is a convenient Command Line Interface (CLI) built on top of
``python-ovh`` and OVH's ReST APIs.

Available command list is generated at runtime based on automatically updated
json schemas of the API.

The name of the API to use is determined by the executable name. For instance,
if runing program is called 'ovh-eu', it will expose european OVH's API', it
will expose european OVH's API's. Currently supported APIs includes:
    - ovh-eu
    - ovh-ca
    - runabove-ca

Future optimizations:
    - use a single cache file to minimize disk access
    - lazy load schemas

'''

from __future__ import absolute_import

import os
import re
import sys
import ovh
import json
import requests
import argparse

try:
    import cPickle as pickle
except ImportError:
    import pickle

from ovh.client import ENDPOINTS

SCHEMAS_BASE_PATH='./schemas/'
#: runtime schema cache to avoid net/disk I/O
SCHEMAS = {}

## argument parse, supports 'url-like' positional argument sequence

ACTION_ALIASES = {
    'get': 'GET',
    'show': 'GET',
    'list': 'GET',
    'post': 'POST',
    'create': 'POST',
    'put': 'PUT',
    'udate': 'PUT',
    'set': 'PUT',
    'delete': 'DELETE',

    # prefixed aliases
    'do_get': 'GET',
    'do_show': 'GET',
    'do_list': 'GET',
    'do_post': 'POST',
    'do_create': 'POST',
    'do_put': 'PUT',
    'do_udate': 'PUT',
    'do_set': 'PUT',
    'do_delete': 'DELETE',
}

class ArgParserException(Exception): pass
class ArgParserTypeConflict(ArgParserException): pass
class ArgParserUnknownRoute(ArgParserException): pass

class ArgParser(object):
    '''
    Recursively parse arbitrary url-like argument list. Internaly, maintains an
    abstract parse tree. Each edge may be of type
      - ``argument`` --> when next expected chunk is an arbitrary argument
      - ``parser`` --> when multiple subpath are possible
      - action --> list of possible actions, namely HTTP Verbs

    ``argument`` and ``parser`` may be mixed. In this case, parser will attempt
    to match a route and then fallback on the argument. If a sub path conficts
    with an action, the route is taken. To force the action, prefix with 'do_'.

    ``action``s are liked to an argparse argument parser containing the list of
    remaining named arguments.

    When hitting a leaf node or end up consuming positional arguments (ie, next
    argument starts with '-' or not more argument), do the default action or
    GET (show/list) by default.

    When hitting a leaf node, try to match an action

    For example, 'me bill random_id' will be parsed to
    '/me/bill/random_id'
    '''
    def __init__(self, name=None, path=None):
        '''
        :param str name: argument name as expected on the command line
                         if ``None``, consider this chunk as an argument
        :param str path: original path chunk name in the URL or variable name
        '''
        self.name = name
        self.path = path
        self._actions = {} #: action_name: action_parser
        self._routes = {} #: route.name: route

    def ensure_parser(self, chunk, path=None):
        '''
        if ``chunk`` starts with '{' set ``name`` and ``path`` to None.
        Otherwise, set name to snake-case path.

        If path is specified, override default one.

        If parser ``name`` already exists, return it. Otherwise, instanciate
        parser and register it.

        :return: parser
        :raise ArgParserTypeConflict: when mixing ``argument`` ``router`` parsers
        '''
        # Is it an argument ?
        if chunk[0] == '{':
            name = None
            path = None
        else:
            name = camel_to_snake(chunk)
            path = path or chunk

        # check duplicated name
        if name in self._routes:
            return self._routes[name]

        # register
        self._routes[name] = ArgParser(name, path)
        return self._routes[name]

    def ensure_path_parser(self, path):
        '''
        Utility function. Ensures that ``path`` will be matchable by this
        parser. If applicablen create intermediate parsers.

        return: leaf parser instance
        '''

        if not path:
            return self

        if path[0] == '/':
            path = path[1:]

        if '/' in path:
            chunk, path = path.split('/', 1)
        else:
            chunk, path = path, ''

        parser = self.ensure_parser(chunk)
        return parser.ensure_path_parser(path)

    def register_http_verb(self, verb, parameters):
        '''
        Register an action. Actions are mapped to HTTP verbs.

        GET    --> list if has an argument child at parse time
        GET    --> show otherwise
        POST   --> create
        PUT    --> update
        DELETE --> delete
        '''
        verb = verb.upper()

        # check duplicated verbs:
        if verb in self._actions:
            raise ArgParserTypeConflict('Duplicated actions %s' % name)

        self._actions[verb] = parameters

    def parse(self, base_url, args):
        '''
        If ``args`` is empty or first arg starts with '-': take an action
        Otherwise, consumes one argument from ``args``:
          - take an action ?
          - route ?

        Disambiguation is done here.

        :returns: verb, path, parsed_arguments
        '''
        # do we have an argument to consume ?
        if args and not args[0].startswith('-'):
            chunk = args.pop(0)

            # is it a route ?
            if chunk in self._routes:
                parser = self._routes[chunk]
                base_url += '/'+parser.name
                return parser.parse(base_url, args)

            # is is an argument ?
            if None in self._routes:
                # TODO: encode argument
                parser = self._routes[None]
                base_url += '/'+chunk
                return parser.parse(base_url, args)

            # is it an action ?
            chunk = chunk.lower()
            if chunk in ACTION_ALIASES and ACTION_ALIASES[chunk] in self._actions:
                verb = ACTION_ALIASES[chunk]
                args = self.parse_action_params(verb, args, base_url)
                return verb, base_url, args

            # Ooops
            raise ArgParserUnknownRoute('Unknwon route %s/%s' % (base_url, chunk))

        # no action neither positional argument: take default action
        else:
            # Do we have actions on this path
            if not self._actions:
                raise ArgParserUnknownRoute('No actions are available for %s' % base_path)

            # A single action: do it (maybe DELETE !)
            if len(self._actions) == 1:
                verb = self._actions.keys()[0]
                args = self.parse_action_params(verb, args, base_url)
                return verb, base_url, args

            # multiple actions, try innocuous 'GET'
            if 'GET' in self._actions:
                verb = 'GET'
                args = self.parse_action_params(verb, args, base_url)
                return verb, base_url, args

            # ambiguous
            raise ArgParserUnknownRoute('No default actions is available for %s. Please pick one manually' % base_path)

    def parse_action_params(self, action, args, base_url):
        '''
        parse remaining positional arguments
        '''
        parser = argparse.ArgumentParser(action+' '+base_url)

        for param in self._actions[action]:
            if param['paramType'] == 'path':
                continue

            type=str
            if param['dataType'] == 'long': type=long
            if param['dataType'] == 'int': type=int
            if param['dataType'] == 'float': type=float
            if param['dataType'] == 'double': type=float
            parser.add_argument(
                    '--'+param['name'],
                    type=type,
                    required=bool(param.get('required', 0)),
                    help=param.get('description', ''),
            )
        return parser.parse_args(args)

## utils

def pretty_print_json(data):
    print json.dumps(
            data,
            sort_keys=True,
            indent=4,
            separators=(',', ': ')
    )

def camel_to_snake(name):
    '''
    from: http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case
    '''
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

def do_get_schema(endpoint, name):
    '''
    Download and cache schema ``name`` in memory.
    '''
    if name in SCHEMAS:
        return SCHEMAS['name']

    url = ENDPOINTS[endpoint]+name

    print "Downloading schema", name
    SCHEMAS[name] = requests.get(url).json()
    return SCHEMAS[name]

def load_schemas(endpoint):
    '''
    Download and installs json API schema for ``client`` and save them for
    future use.
    '''
    root_schema = do_get_schema(endpoint, '/')

    for api in root_schema['apis']:
        schema_name = api['schema'].format(path=api['path'], format='json')
        do_get_schema(endpoint, schema_name)

def init_arg_parser(endpoint, refresh=False):
    '''
    Build command line parser from json and cache result on disk for faster
    load.

    As there is (currently) no ambiguity, always take only the second part of
    the 'resourcePath' as command name. For instance, '/hosting/privateDatabase'
    leads to 'private-database'.

    All command line arguments are converted to snake-case.

    :param str endpoint: api endpoint name.
    :param boolean refresh: when ``True``, bypass cache, no matter its state.
    '''

    cache_file = SCHEMAS_BASE_PATH+endpoint

    # First attempt to load parser from cache
    try:
        with open(cache_file, 'r') as f:
            return pickle.load(f)
    except:
        pass

    # cache dir exists ?
    if not os.path.exists(SCHEMAS_BASE_PATH):
        os.makedirs(SCHEMAS_BASE_PATH)

    # get schemas
    load_schemas(endpoint)

    # Build parser
    parser = ArgParser('root', '')

    for schema in SCHEMAS.values():
        if not 'resourcePath' in schema:
            continue

        # add root command
        base_path = schema['resourcePath']
        api_cmd = os.path.basename(base_path)
        api_parser = parser.ensure_parser(api_cmd, base_path)

        # add subcommands

        for api in schema['apis']:
            command_path = api['path'][len(base_path):]
            command_parser = api_parser.ensure_path_parser(command_path)

            # add actions
            for operation in api['operations']:
                command_parser.register_http_verb(
                        operation['httpMethod'], 
                        operation['parameters'])

    # cache resulting parser
    with open(cache_file, 'w') as f:
        return pickle.dump(parser, f, pickle.HIGHEST_PROTOCOL)

    return parser

if __name__ == '__main__':
    # load and validate endpoint name from cli name
    endpoint = os.path.basename(sys.argv[0])
    if endpoint not in ENDPOINTS:
        print >> sys.stderr, "Unknown endpoint", endpoint
        sys.exit(1)

    # create argument parser
    parser = init_arg_parser(endpoint)

    print parser.parse(ENDPOINTS[endpoint], sys.argv[1:])

