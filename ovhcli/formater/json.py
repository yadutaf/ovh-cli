# -*- encoding: utf-8 -*-

import json

def do_format(client, verb, method, arguments):
    data = getattr(client, verb.lower())(method, **arguments)

    print json.dumps(
        data,
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    )

