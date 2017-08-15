#!/usr/bin/env python

import json, threading, time
import epics

from bottle import route, run, static_file, redirect, abort
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
            #for pv in CONFIG['PVs']:
            #    if pv['name'] != kwargs['pvname']: continue
            #    pv['unit'] = p.units or ''
        tid = threading.Thread(target=fetch_ctrlvars)
        tid.daemon = True
        tid.start()
        return

    # Otherwise: we are disconnected from the IOC!
    for pv in CONFIG['PVs']:
        if pv['name'] != kwargs['pvname']: continue

        pv['value'] = '- disconnected -'
        pv['unit'] = ''
        pv['classes'] = 'disconnected'
        pv['precision'] = None


def cb_value_update(**kwargs):
    global CONFIG
    for pv in CONFIG['PVs']:
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
        pv['precision'] = kwargs['precision']
        #if type(kwargs['precision']) == int and ('double' in kwargs['type'] or 'float' in kwargs['type']):
        #    pv['value'] = round(pv['value'], kwargs['precision'])
        if kwargs['enum_strs'] == (b'OFF', b'ON'):
            pv['classes'] += ' switch'
        if pv['value'] is None: pv['value'] = '- disconnected -'
        pv['unit'] = kwargs['units'] or ''
        if pv['unit'] == 'deg C': pv['unit'] = '&degC'
        if pv['unit'] == 'g/m3': pv['unit'] = 'g/m&sup3'

@route('/')
def index():
    redirect('/list/general_overview')

@route('/list/<page>')
@view('pv_overview.jinja2')
def list_pvs(page):
    if page not in CONFIG['pages']:
        return abort(404, 'Page not found')
    return {'config': CONFIG, 'req_page': page}

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

    CONFIG['PV_lookup'] = {}

    for i, pv in enumerate(CONFIG['PVs']):
        pv['value'] = '- disconnected (initial) -'
        pv['unit'] = ''
        pv['precision'] = None
        pv['classes'] = 'disconnected'
        PVS[pv['name']] = epics.PV(pv['name'], auto_monitor=True, form='ctrl', callback=cb_value_update, connection_callback=cb_connection_change)
        CONFIG['PV_lookup'][pv['name']] = i

    run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__": main()
