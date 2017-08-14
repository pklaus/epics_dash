#!/usr/bin/env python

import json, threading, time
import epics

from bottle import route, run, static_file
from bottle import jinja2_view as view

CONFIG = None
PVS = {}

def cb_connection_change(**kwargs):
    global CONFIG

    if kwargs['conn']:
        pass
        # We are now connected
        def fetch_ctrlvars():
            #print("Started thread for ", kwargs['pvname'])
            #start = time.time()
            p = PVS[kwargs['pvname']]
            p.get_ctrlvars()
            #end = time.time()
            #print("Finished thread for ", kwargs['pvname'], " in ", end-start, " s. Unit: ", p.units)
            #for group in CONFIG['groups']:
            #    for pv in group['PVs']:
            #        if pv['name'] != kwargs['pvname']: continue
            #        pv['unit'] = p.units or ''
        tid = threading.Thread(target=fetch_ctrlvars)
        tid.daemon = True
        tid.start()
        return

    # Otherwise: we are disconnected from the IOC!
    for group in CONFIG['groups']:
        for pv in group['PVs']:
            if pv['name'] != kwargs['pvname']: continue

            pv['value'] = '- disconnected -'
            pv['unit'] = ''
            pv['classes'] = 'disconnected'


def cb_value_update(**kwargs):
    global CONFIG
    for group in CONFIG['groups']:
        for pv in group['PVs']:
            if pv['name'] != kwargs['pvname']: continue

            class_map = {
              epics.NO_ALARM :      "",
              epics.MINOR_ALARM :   "minor_alarm",
              epics.MAJOR_ALARM :   "major_alarm",
              epics.INVALID_ALARM : "invalid_alarm",
              None : "disconnected",
            }
            pv['classes'] = class_map[kwargs['severity']]
            #print(kwargs['pvname'], kwargs['type'])
            #print(kwargs)
            if 'enum' in kwargs['type']:
                if type(kwargs['char_value']) is bytes:
                     pv['value'] = kwargs['char_value'].decode('ascii')
                else:
                     pv['value'] = kwargs['char_value']
            else:
                pv['value'] = kwargs['value']
            if pv['value'] is None: pv['value'] = '- disconnected -'
            pv['unit'] = kwargs['units'] or ''
            if pv['value'] == 'OFF': pv['value'] = '- OFF -'
            if pv['value'] == 'ON': pv['value'] = '- ON -'

@route('/')
@view('pv_overview.jinja2')
def index():
    return CONFIG

@route('/api/values.json')
def index():
    return CONFIG

@route('/static/<path:path>')
def static_content(path):
    return static_file(path, root='./static/')

def main():
    global CONFIG, PVS

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

    for group in CONFIG['groups']:
        for pv in group['PVs']:
            pv['value'] = '- disconnected (initial) -'
            pv['unit'] = ''
            pv['classes'] = 'disconnected'
            PVS[pv['name']] = epics.PV(pv['name'], auto_monitor=True, form='ctrl', callback=cb_value_update, connection_callback=cb_connection_change)

    run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__": main()
