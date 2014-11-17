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
    - kimsufi-eu
    - kimsufi-ca
    - soyoustart-eu
    - soyoustart-ca
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
import sys
import ovh

from ovhcli.utils import camel_to_snake
from ovhcli.schema import load_schemas, SCHEMAS_BASE_PATH, SCHEMAS
from ovhcli.formater import formaters, get_formater
from ovhcli.parser import ArgParser
from ovhcli.parser import ArgParserException, ArgParserTypeConflict, ArgParserUnknownRoute

try:
    import cPickle as pickle
except ImportError:
    import pickle

from ovh.client import ENDPOINTS

## parser

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
    load_schemas(ENDPOINTS[endpoint])

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
        'debug': False,
        'refresh': False,
        'help': False,
        'format': 'terminal', # or 'json'
    }

    # load and validate endpoint name from cli name
    endpoint = os.path.basename(sys.argv[0])
    if endpoint not in ENDPOINTS:
        print >> sys.stderr, "Unknown endpoint", endpoint
        sys.exit(1)

    args = sys.argv[1:]

    # special/top level arguments:
    while args and args[0].startswith('--'):
        arg = args.pop(0)
        if arg == '--refresh':
            options['refresh'] = not options['refresh']
        if arg == '--debug':
            options['debug'] = not options['debug']
        if arg == '--help':
            options['help'] = not options['help']
        if arg == '--format':
            try: options['format'] = args.pop(0)
            except IndexError: pass

            if options['format'] not in formaters:
                print >>sys.stderr, 'Invalid format %s, expected one of %s' % (options['format'], ', '.join(formaters.keys()))
                sys.exit(1)

    # create argument parser
    parser = init_arg_parser(endpoint, options['refresh'])

    if options['help']:
        do_usage()
        print parser.get_help_message()
        sys.exit(1)

    # Ensure enough arguments
    if not args:
        do_usage()
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
    formater = get_formater(options['format'])
    try:
      formater.do_format(client, verb, method, arguments.__dict__)
    except Exception as e:
      # print noce error message
      print e

      # when in debug mode, re-raise to see the full stack-trace
      if options['debug']:
        raise

