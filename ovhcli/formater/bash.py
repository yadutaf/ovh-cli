# -*- encoding: utf-8 -*-

import re

from ovhcli.utils import camel_to_bash, pretty_print_value_scalar

PREFIX="OVH_"

def bash_pretty_print_value_scalar(data):
	data = str(pretty_print_value_scalar(data))
	data = re.escape(data)
	return data

def do_format(client, verb, method, arguments):
    data = getattr(client, verb.lower())(method, **arguments)

    if isinstance(data, list):
    	print PREFIX+"LIST='"+' '.join(data)+"'"
    elif isinstance(data, dict):
    	for key, value in data.iteritems():
    		print PREFIX+camel_to_bash(key)+"="+bash_pretty_print_value_scalar(value)
    else:
		print PREFIX+"VALUE="+bash_pretty_print_value_scalar(value)
