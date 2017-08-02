#!/usr/bin/env python

import json
import epics

from bottle import route, run, static_file
from bottle import jinja2_view as view

CONFIG = None

@route('/')
@view('pv_overview.jinja2')
def index():
    global CONFIG
    for group in CONFIG['groups']:
        for pv in group['PVs']:
            p = epics.PV(pv['name'])
            p.get_ctrlvars()
            if 'enum' in p.type:
                pv['value'] = p.get(as_string=True)
            else:
                pv['value'] = p.get()
            pv['unit'] = p.units or ''
    return CONFIG

@route('/static/<path:path>')
def static_content(path):
    return static_file(path, root='./static/')

def main():
    global CONFIG

    import argparse
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
        CONFIG = json.load(f)

    run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__": main()
