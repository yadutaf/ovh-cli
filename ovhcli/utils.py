# -*- encoding: utf-8 -*-

import re
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

def camel_to_bash(name):
    '''
    upper case + underscore
    '''
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s1 = s1.replace('/', '-')
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).upper()

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
        return str(data)
