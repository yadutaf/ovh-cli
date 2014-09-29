# -*- encoding: utf-8 -*-

import requests

SCHEMAS_BASE_PATH='./schemas/'
#: runtime schema cache to avoid net/disk I/O
SCHEMAS = {}

def do_get_schema(endpoint, name):
    '''
    Download and cache schema ``name`` in memory.
    '''
    if name in SCHEMAS:
        return SCHEMAS['name']

    url = endpoint+name

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
