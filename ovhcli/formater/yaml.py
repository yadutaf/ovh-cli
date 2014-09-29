# -*- encoding: utf-8 -*-

from __future__ import absolute_import

import pyaml

def do_format(client, verb, method, arguments):
    data = getattr(client, verb.lower())(method, **arguments)
    print pyaml.dump(data)
