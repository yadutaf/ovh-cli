# -*- encoding: utf-8 -*-

import pkgutil
import imp

# HACK: ensure yaml/json lib in cache is the global one:
import yaml
import json

formaters = dict([(name, importer) for importer, name, _ in pkgutil.iter_modules(['ovhcli/formater'])])

def get_formater(name):
	return formaters[name].find_module(name).load_module(name)
