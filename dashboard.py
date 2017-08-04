#!/usr/bin/env python

import json
import epics

from bottle import route, run, static_file
from bottle import jinja2_view as view

CONFIG = None

def update_values():
    global CONFIG
    for group in CONFIG['groups']:
        for pv in group['PVs']:
            p = epics.PV(pv['name'])
            p.get_ctrlvars()
            class_map = {
              epics.NO_ALARM :      "",
              epics.MINOR_ALARM :   "minor_alarm",
              epics.MAJOR_ALARM :   "major_alarm",
              epics.INVALID_ALARM : "invalid_alarm",
            }
            pv['classes'] = class_map[p.severity]
            if 'enum' in p.type:
                pv['value'] = p.get(as_string=True)
            else:
                pv['value'] = p.get()
            pv['unit'] = p.units or ''

@route('/')
@view('pv_overview.jinja2')
def index():
    update_values()
    return CONFIG

@route('/api/values.json')
def index():
    update_values()
    return CONFIG

@route('/static/<path:path>')
def static_content(path):
    return static_file(path, root='./static/')

def main():
    global CONFIG

    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='',
          help='The host (IP address) the web server should listen on.')
    parser.add_argument('--port', default=4913,
          help='The port the web server should listen on.')
    parser.add_argument('--config', '-c', required=True,
          help='The config file with the definition of process variables and EPICS hosts.')
    parser.add_argument('--debug', action='store_true',
          help='Set the debug mode of the web server.')
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        try:
            CONFIG = json.load(f)
        except Exception as e:
            sys.stderr.write("Error loading --config file.\n")
            sys.stderr.write(str(e) + "\n")
            sys.exit(1)

    run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__": main()
