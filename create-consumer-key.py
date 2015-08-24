#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Helper to generate OVH API consumer key. In a nutshell, the consumer key
identifies a specific user in an application while application key and
application secret identifies the application itself. In the case of ovh-cli
each instance of the CLI must hav its own, dedicated, set of credentials.

To generate application secret and application key, please visit:
    - OVH Europe: https://eu.api.ovh.com/createApp/
    - OVH North America: https://ca.api.ovh.com/createApp/
    - Soyoustart Europe: https://eu.api.soyoustart.com/createApp/
    - Soyoustart North America: https://ca.api.soyoustart.com/createApp/
    - Kimsufi Europe: https://eu.api.kimsufi.com/createApp/
    - Kimsufi North America: https://ca.api.kimsufi.com/createApp/
    - Runabove North America: https://api.runabove.com/createApp/

You may then request a consumer key using this tool:

    $ create-consumer-key.py [endpoint]

Where ``endpoint`` may be one of ``ovh-eu``, ``ovh-ca``, and so on.

Once generated, your application key, application secret and consumer key
must be set in eiter:
    - ``./ovh.conf`` for an application specific configuration
    - ``$HOME/.ovh.conf`` for a user wide configuration
    - ``/etc/ovh.conf`` for a system wide / server configuration

This file will look like:

    [default]
    endpoint=ovh-eu

    [ovh-eu]
    application_key=my_app_key
    application_secret=my_application_secret
    ;consumer_key=my_consumer_key

Alternatively, at runtime, configuration may be overloaded using environment
variables. For more informations regarding available configuration options,
please see https://github.com/ovh/python-ovh
'''

import sys
import ovh

# Load api endpoint from command line, if any
if len(sys.argv) == 1:
    endpoint=None
elif len(sys.argv) == 2:
    endpoint=sys.argv[1]
else:
    print >>sys.stderr, __doc__
    sys.exit(1)

if endpoint in ['-h', '--help']:
    print >>sys.stderr, __doc__
    sys.exit(0)

# Create a client using configuration
try:
    client = ovh.Client(endpoint)
except Exception as e:
    print e
    print >>sys.stderr, __doc__
    sys.exit(1)

# Request full API access
access_rules = [
    {'method': 'GET', 'path': '/*'},
    {'method': 'POST', 'path': '/*'},
    {'method': 'PUT', 'path': '/*'},
    {'method': 'DELETE', 'path': '/*'}
]

# Request token
validation = client.request_consumerkey(access_rules)

print "Please visit %s to authenticate" % validation['validationUrl']
raw_input("and press Enter to continue...")

# Print nice welcome message
print "Welcome", client.get('/me')['firstname']
print "Here is your Consumer Key: '%s'" % validation['consumerKey']

