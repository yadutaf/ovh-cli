# -*- encoding: utf-8 -*-

import urllib
import datetime
import tabulate
import textwrap

from ovhcli.utils import grouped, camel_to_snake, camel_to_human, pretty_print_value_scalar

## utils

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

def pretty_print_table(data, max_col_width=50, headers=None):
    # redy to print lines
    table = []
    n_col = len(data[0])

    # build lines + compute max width
    col_width = [0]*n_col
    for line in data:
        line_lines = []
        for i, cell in enumerate(line):
            cell = pretty_print_value(cell)
            col_width[i] = max(col_width[i], min(len(cell), max_col_width))
            cell_lines = textwrap.wrap(cell, max_col_width)

            for j, cell_line in enumerate(cell_lines):
                if j >= len(line_lines):
                    line_lines.append(['']*n_col)
                line_lines[j][i] = cell_line
        table += line_lines

    # print table
    return tabulate.tabulate(table, headers=headers or [])

## entry point

def do_format(client, verb, method, arguments):
    data = getattr(client, verb.lower())(method, **arguments)

    # looks a *lot* like a listing: get all elements
    if verb == 'GET'\
       and isinstance(data, list)\
       and data and isinstance(data[0], (int, long, str, unicode)):

        table = []
        for elem in data:
            line = client.get(method+'/'+urllib.quote_plus(str(elem)))
            line_data = [elem]
            for item in line.values():
                line_data.append(item)
            table.append(line_data)
        headers = ['ID']+[camel_to_human(str(title)) for title in line.keys()]
        print pretty_print_table(table, headers=headers, max_col_width=50)
    elif isinstance(data, dict):
        if not data:
            print "{}"
        # xdsl plots
        elif sorted(data.keys()) == [u'unit', u'values']:
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
            print pretty_print_table(table, max_col_width=100)
    elif isinstance(data, list):
        if not data:
            print "[]"
        elif isinstance(data[0], dict):
            table = []
            for line in data:
                line_data = []
                for item in line.values():
                    line_data.append(item)
                table.append(line_data)
            headers = [camel_to_human(str(title)) for title in line.keys()]
            print pretty_print_table(table, headers=headers, max_col_width=50)
        else:
            for value in data:
                print pretty_print_value_scalar(value)
    elif isinstance(data, (int, long, float, unicode, str)):
        print pretty_print_value_scalar(data)
    elif not data:
        print "Success"
    else:
      # Should no be here...
      print data

