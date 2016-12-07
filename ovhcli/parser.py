# -*- encoding: utf-8 -*-
'''
Argument parser, supports 'url-like' positional argument sequence
'''

import json
import urllib
import argparse

from ovhcli.utils import camel_to_snake

ACTION_ALIASES = {
    'get': 'GET',
    'show': 'GET',
    'list': 'GET',
    'post': 'POST',
    'create': 'POST',
    'put': 'PUT',
    'update': 'PUT',
    'set': 'PUT',
    'delete': 'DELETE',

    # prefixed aliases
    'do_get': 'GET',
    'do_show': 'GET',
    'do_list': 'GET',
    'do_post': 'POST',
    'do_create': 'POST',
    'do_put': 'PUT',
    'do_update': 'PUT',
    'do_set': 'PUT',
    'do_delete': 'DELETE',
}

class ArgParserException(Exception): pass
class ArgParserTypeConflict(ArgParserException): pass
class ArgParserUnknownRoute(ArgParserException): pass

def parse_bool(data):
    data = data.lower().strip()
    if data in ['', '0', 'off', 'false', 'no']:
        return False
    return True

def schema_datatype_to_type(datatype):
    if datatype == 'string': return str
    if datatype == 'text':   return str
    if datatype == 'long':   return long
    if datatype == 'int':    return int
    if datatype == 'float':  return float
    if datatype == 'double': return float
    if datatype == 'boolean': return parse_bool
    if datatype in ['ip', 'ipBlock']: return str
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
            # chunk = chunk.lower()
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
                print self.get_help_message()
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

    def _register_parser_command(self, parser, action, name, type, required, description):
        choices = None
        description = description or ''
        description = description.replace('%', '%%') # Encode description to fix some help printing

        # Decode datatype
        is_array = type.endswith('[]')
        if is_array:
            type = type[:-2]
            description = '(list) '+description
        datatype = schema_datatype_to_type(type)

        # Decode complex data types
        if datatype is None:
            if type in self.schema['models']:
                model = self.schema['models'][type]
                if 'enum' in model:
                    datatype = schema_datatype_to_type(model['enumType'])
                    choices = model['enum']
                elif 'properties' in model:
                    datatype = json.loads
                else:
                    datatype = str
            else:
                datatype = str

        # Never require a '--' (not part of the path) parameter on PUT
        if action == "PUT":
            required = False

        # Register command
        parser.add_argument(
                '--'+name,
                type=datatype,
                action='append' if is_array else 'store',
                required=required,
                help=description,
                default=argparse.SUPPRESS,
                choices=choices,
        )

    def parse_action_params(self, action, args, base_url):
        '''
        parse remaining positional arguments
        '''
        parser = argparse.ArgumentParser(action+' '+base_url)

        for param in self._actions[action]['parameters'] or []:
            if param['paramType'] == 'path':
                continue

            # For PUT case, we need to add individual fields of the object to edit
            typename = param.get('dataType')
            if action == "PUT" and typename in self.schema['models']:
                model = self.schema['models'][typename]
                for name, prop in model['properties'].iteritems():
                    if prop.get('readOnly', 1) != 0:
                        continue

                    self._register_parser_command(
                        parser,
                        action,
                        name,
                        prop['type'],
                        not bool(prop.get('canBeNull', 0)),
                        prop.get('description', ''),
                    )
            else:
                self._register_parser_command(
                    parser,
                    action,
                    param.get('name'),
                    typename,
                    bool(param.get('required', 0)),
                    param.get('description', ''),
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
        else:
            msg += ":\n\n"

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
