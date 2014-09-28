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

TODO:
 - list / complete 'enum' arguments

Usage: General: {cli} [--help|--refresh|--format (pretty|json)] your command and args --param value --param2 value2
       Get help on a specific path: {cli} your command --help
       Get help on a specific action: {cli} your command (list|show|update|create|delete) --help

Note: if requested action conflicts with an API action the API action will be
      executed. To force the action, prefix it with 'do_'. Fo instance, 'list'
      becomes 'do_list'

Top level options:
    --help      This message
    --refresh   Rebuild available commands list and documentation
    --format    Output format, can be 'pretty' or 'json'. (default='pretty')
'''

from __future__ import absolute_import

import os
import re
import sys
import ovh
import json
import requests
import argparse
import tabulate
import datetime
import urllib
from itertools import izip

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

def schema_datatype_to_type(datatype):
    if datatype == 'string': return str
    if datatype == 'long':   return long
    if datatype == 'int':    return int
    if datatype == 'float':  return float
    if datatype == 'double': return float
    return None

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
    def __init__(self, name=None, path=None, help="", schema=None):
        '''
        :param str name: argument name as expected on the command line
                         if ``None``, consider this chunk as an argument
        :param str path: original path chunk name in the URL or variable name
        :param str help: help string for this level
        '''
        self.name = name
        self.path = path
        self.help = ""
        self.schema = schema or {'models': {}}
        self._actions = {} #: action_name: action_parser
        self._routes = {} #: route.name: route

    def ensure_parser(self, chunk, path=None, help="", schema=None):
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
            path = chunk
        else:
            name = camel_to_snake(chunk)
            path = path or chunk

        # check duplicated name
        if name in self._routes:
            return self._routes[name]

        # register
        self._routes[name] = ArgParser(name, path, help, schema)
        return self._routes[name]

    def ensure_path_parser(self, path, help="", schema=None):
        '''
        Utility function. Ensures that ``path`` will be matchable by this
        parser. If applicablen create intermediate parsers.

        :param str path: the path to ensure in the API
        :param str help: Help message assiciated with leaf element
        :return: leaf parser instance
        '''

        if not path:
            self.help = help
            return self

        if path[0] == '/':
            path = path[1:]

        if '/' in path:
            chunk, path = path.split('/', 1)
        else:
            chunk, path = path, ''

        parser = self.ensure_parser(chunk, schema=schema)
        return parser.ensure_path_parser(path, help, schema)

    def register_http_verb(self, verb, parameters, help):
        '''
        Register an action. Actions are mapped to HTTP verbs.

        GET    --> list if has an argument child at parse time
        GET    --> show otherwise
        POST   --> create
        PUT    --> update
        DELETE --> delete

        :param str help: help message for this action
        '''
        verb = verb.upper()

        # check duplicated verbs:
        if verb in self._actions:
            raise ArgParserTypeConflict('Duplicated actions %s' % name)

        self._actions[verb] = {
            'parameters': parameters,
            'help': help,
        }

    def parse(self, base_url, args):
        '''
        If ``args`` is empty or first arg starts with '-': take an action
        Otherwise, consumes one argument from ``args``:
          - take an action ?
          - route ?

        Disambiguation is done here.

        :returns: verb, path, parsed_arguments
        '''
        # are we asked some help ?
        if args and args[0] == '--help':
            print self.get_help_message()
            return None, None, None

        # do we have an argument to consume ?
        elif args and not args[0].startswith('-'):
            chunk = args.pop(0)

            # is it a route ?
            if chunk in self._routes:
                parser = self._routes[chunk]
                base_url += '/'+parser.path
                return parser.parse(base_url, args)

            # is it an action ?
            chunk = chunk.lower()
            if chunk in ACTION_ALIASES and ACTION_ALIASES[chunk] in self._actions:
                verb = ACTION_ALIASES[chunk]
                args = self.parse_action_params(verb, args, base_url)
                return verb, base_url, args

            # is is an argument ?
            if None in self._routes:
                # TODO: encode argument
                parser = self._routes[None]
                base_url += '/'+urllib.quote_plus(chunk)
                return parser.parse(base_url, args)

            # Ooops
            raise ArgParserUnknownRoute('Unknown route %s/%s' % (base_url, chunk))

        # no action neither positional argument: take default action
        else:
            # Do we have actions on this path
            if not self._actions:
                raise ArgParserUnknownRoute('No actions are available for %s' % base_url)

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
            raise ArgParserUnknownRoute('No default actions is available for %s. Please pick one manually' % base_url)

    def parse_action_params(self, action, args, base_url):
        '''
        parse remaining positional arguments
        '''
        parser = argparse.ArgumentParser(action+' '+base_url)

        for param in self._actions[action]['parameters']:
            if param['paramType'] == 'path':
                continue

            # decode datatype
            datatype = schema_datatype_to_type(param['dataType'])
            choices = None

            if datatype is None:
                if param['dataType'] in self.schema['models']:
                    model = self.schema['models'][param['dataType']]
                    if 'enum' in model:
                        datatype = schema_datatype_to_type(model['enumType'])
                        choices = model['enum']
                else:
                    datatype = str

            parser.add_argument(
                    '--'+param['name'],
                    type=datatype,
                    required=bool(param.get('required', 0)),
                    help=param.get('description', ''),
                    default=argparse.SUPPRESS,
                    choices=choices,
            )
        return parser.parse_args(args)

    def get_help_message(self):
        msg = ''

        if self.name is not None:
            # This a regular path chunk
            msg = "Method '"+self.name+"'"
        elif self.path is not None:
            # this is a parameter
            msg = "Param '"+self.path+"'"

        # do we have doc ?
        if self.help:
            if msg:
                msg += ': '+self.help
            else:
                msg = self.help
            msg +='\n\n'

        # list actions
        if self._actions:
            action_helps = ["Actions:"]
            for name, action in self._actions.iteritems():
                # title
                if name == 'GET':
                    if None in self._routes: action_title='list'
                    else: action_title='show'
                elif name == 'POST': action_title='create'
                elif name == 'PUT': action_title='update'
                else: action_title=name.lower()

                # do we have an help message ?
                if action['help']:
                    description = action['help']
                else:
                    description = action_title.capitalize()+" "+self.name or self.path+" object(s)"

                # default
                if name == 'GET': description += ' (default)'
                elif len(self._actions) == 1: description += ' (default)'

                action_helps.append("    %-7s %s" % (action_title, description))
            msg += '\n'.join(action_helps)+'\n\n'

        # list routes
        if self._routes:
            routes_help = ["Methods:"]
            routes_table = []
            for name, route in self._routes.iteritems():
                routes_table.append((
                    '' + (route.name or route.path),
                    route.help,
                ))
            colw = max((len(x) for x,y in routes_table))
            fmt = "    %-"+str(colw)+'s %s'
            for line in routes_table:
                routes_help.append(fmt % line)
            msg += '\n'.join(routes_help)+'\n\n'

        return msg

## utils

from itertools import izip

def grouped(iterable, n):
    '''
    source: http://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list
    '''
    return izip(*[iter(iterable)]*n)

def camel_to_snake(name):
    '''
    from: http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-camel-case
    '''
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    s1 = s1.replace('/', '-')
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

def camel_to_human(name):
    '''
    add spaces between words.
    '''
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1).capitalize()

def pretty_print_value_scalar(data):
    # float data ?
    if isinstance(data, float):
        return "%.3f" % data
    elif isinstance(data, (str, unicode)):
        return camel_to_human(data)
    # fallback
    else:
        return unicode(data)

def pretty_print_value_dict(data):
    # values ?
    if sorted(data.keys()) == [u'unit', u'value']:
        return u"%s%s" % (pretty_print_value_scalar(data['value']), data['unit'])
    # prices
    if sorted(data.keys()) == [u'currencyCode', u'text', u'value']:
        return pretty_print_value_scalar(data['text'])
    # fallback
    else:
        return str(data)

def pretty_print_value_list(data):
    # values ?
    if data:
        return ', '.join([pretty_print_value_scalar(x) for x in data])
    # fallback
    else:
        return '<empty list>'

def pretty_print_value(data):
    if isinstance(data, (int, long, float)):
        return pretty_print_value_scalar(data)
    elif isinstance(data, dict):
        return pretty_print_value_dict(data)
    elif isinstance(data, list):
        return pretty_print_value_list(data)
    else:
        return unicode(data)

## formaters

def pretty_print_json(client, verb, method, arguments):
    data = getattr(client, verb.lower())(method, **arguments)

    print json.dumps(
        data,
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    )

def pretty_print_terminal(client, verb, method, arguments):
    data = getattr(client, verb.lower())(method, **arguments)

    # looks a *lot* like a listing: get all elements
    if verb == 'GET'\
       and isinstance(data, list)\
       and data and isinstance(data[0], (int, long, str, unicode)):

        table = []
        for elem in data:
            line = client.get(method+'/'+urllib.quote_plus(elem))
            line_data = [elem]
            for item in line.values():
                line_data.append(pretty_print_value(item))
            table.append(line_data)
        headers = ['ID']+[camel_to_human(title) for title in line.keys()]
        print tabulate.tabulate(table, headers=headers)
    elif isinstance(data, dict):
        # xdsl plots
        if sorted(data.keys()) == [u'unit', u'values']:
            # get points
            xs = [d['timestamp'] for d in data['values']]
            ys = [d['value'] for d in data['values']]

            # get y scale
            count = len(ys)

            ymax = max(ys)
            yscale = 1.0
            unit = data['unit']

            if ymax > 1000*1000*1000:
                yscale = 1000*1000*1000
                unit = 'G'+unit
            elif ymax > 1000*1000:
                yscale = 1000*1000
                unit = 'M'+unit
            elif ymax > 1000:
                yscale = 1000
                unit = 'k'+unit

            # downscale on x too. Try to get close to 50 with only power of 2
            xscale = 2**(int(round(count/50.0))-1).bit_length()
            values = data['values']
            values += [None]*(4-count%4) # padding
            points = grouped(values, xscale)

            for point_g in points:
                # aggregate on last date
                value = 0.0
                divider = 0
                for point in point_g:
                    if point is None: break
                    value += point['value']
                    divider += 1
                    date = datetime.datetime.fromtimestamp(point['timestamp']).strftime('%d/%m/%Y %H:%M')

                value = value / divider / yscale
                bar = '.'*int(value/(ymax/yscale)*80)
                print '%s %3.3f %s | %s' % (date, value, unit, bar)
        else:
            table = []
            for key, value in data.iteritems():
                key = pretty_print_value_scalar(key)
                value = pretty_print_value(value)
                table.append((key, value))
            print tabulate.tabulate(table)
    elif isinstance(data, list):
        for value in data:
            print pretty_print_value_scalar(data)
    elif isinstance(data, (int, long, float, unicode, str)):
        print pretty_print_value_scalar(data)
    else:
        # Well, we should not be there, that's just in case...
        print json.dumps(
            data,
            sort_keys=True,
            indent=4,
            separators=(',', ': ')
        )

FORMATERS = {
    'json': pretty_print_json,
    'pretty': pretty_print_terminal,
}

## parser

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
    print ""

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
        if not refresh:
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
    parser = ArgParser(None, None)

    for schema in SCHEMAS.values():
        if not 'resourcePath' in schema:
            continue

        # add root command
        base_path = schema['resourcePath']
        api_cmd = camel_to_snake(base_path[1:])
        api_parser = parser.ensure_parser(api_cmd, base_path[1:])

        # add subcommands
        for api in schema['apis']:
            command_path = api['path'][len(base_path):]
            command_parser = api_parser.ensure_path_parser(command_path, api['description'], schema)

            # add actions
            for operation in api['operations']:
                command_parser.register_http_verb(
                        operation['httpMethod'],
                        operation['parameters'],
                        operation['description']
                )

    # cache resulting parser
    with open(cache_file, 'w') as f:
        pickle.dump(parser, f, pickle.HIGHEST_PROTOCOL)

    return parser

def do_usage():
    print sys.modules[__name__].__doc__.format(cli=sys.argv[0])

if __name__ == '__main__':
    options = {
        'refresh': False,
        'help': False,
        'format': 'pretty', # or 'json'
    }

    # load and validate endpoint name from cli name
    endpoint = os.path.basename(sys.argv[0])
    if endpoint not in ENDPOINTS:
        print >> sys.stderr, "Unknown endpoint", endpoint
        sys.exit(1)

    # Ensure enough arguments
    args = sys.argv[1:]
    if not args:
        do_usage()
        sys.exit(1)

    # special/top level arguments:
    while args and args[0].startswith('--'):
        arg = args.pop(0)
        if arg == '--refresh':
            options['refresh'] = not options['refresh']
        if arg == '--help':
            options['help'] = not options['help']
        if arg == '--format':
            try: options['format'] = args.pop(0)
            except IndexError: pass

            if options['format'] not in FORMATERS:
                print >>sys.stderr, 'Invalid format %s, expected one of %s' % (options['format'], ', '.join(FORMATERS))
                sys.exit(1)

    # create argument parser
    parser = init_arg_parser(endpoint, options['refresh'])

    if options['help']:
        do_usage()
        print parser.get_help_message()
        sys.exit(1)

    try:
        verb, method, arguments = parser.parse('', args)
    except ArgParserUnknownRoute as e:
        print e
        sys.exit(1)

    if verb is None:
        # abort
        sys.exit(0)

    client = ovh.Client(endpoint)
    FORMATERS[options['format']](client, verb, method, arguments.__dict__)
