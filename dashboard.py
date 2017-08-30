#!/usr/bin/env python

import json, threading, time, copy, math

import simplejson
import epics
from bottle import route, run, static_file, redirect, abort, response, HTTPResponse
from bottle import jinja2_view as view

CONFIG = None
PVS = {}
HISTORY = {}
GC_LAST_RUN = time.time()
HISTORY_LENGTH=30*60

# ------------ History management functions ------------

def history_garbage_collection():
    global HISTORY, GC_LAST_RUN
    if GC_LAST_RUN > (time.time() - 5):
        return
    GC_LAST_RUN = time.time()
    for pv_name in HISTORY:
        # delete entries older than HISTORY_LENGTH (but leave at least one entry older than that in the list)
        while (len(HISTORY[pv_name]) >= 2) and (HISTORY[pv_name][1][0] < (time.time()-HISTORY_LENGTH)):
            del HISTORY[pv_name][0]

def register_pv_value_in_history(pv_name, ts, value):
    global HISTORY
    if pv_name not in HISTORY:
        HISTORY[pv_name] = []
    # If we are asked to put a float:NaN value into the history,
    # repeat the previous value just before our new NaN value
    # This is important to extend plot lines until the value gets invalid.
    if len(HISTORY[pv_name]) > 0 and value is None:
        HISTORY[pv_name].append( [ts-0.1, HISTORY[pv_name][-1][1]] )
    HISTORY[pv_name].append( [ts, value] )

# ------------ Callback functions for the PyEpics Channel Access events ------------

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

        pv['value'] = float('nan')
        pv['char_value'] = 'disconnected'
        pv['num_value'] = float('nan')
        #pv['unit'] = ''
        pv['classes'] = 'disconnected'
        #pv['precision'] = None
        register_pv_value_in_history(kwargs['pvname'], time.time(), float('nan'))


def cb_value_update(**kwargs):
    global CONFIG
    for pv in CONFIG['PVs']:
        if pv['name'] != kwargs['pvname']: continue

        history_garbage_collection()
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
        pv['num_value'] = kwargs['value']
        pv['char_value'] = kwargs['value']
        if kwargs['severity'] == epics.INVALID_ALARM:
            # avoid NaN (cannot be encoded in JSON) and outdated values if invalid
            pv['value'] = float('nan')
            pv['num_value'] = float('nan')
            pv['char_value'] = 'invalid'
        register_pv_value_in_history(kwargs['pvname'], kwargs['timestamp'], pv['num_value'])
        pv['precision'] = kwargs['precision']
        #if type(kwargs['precision']) == int and ('double' in kwargs['type'] or 'float' in kwargs['type']):
        #    pv['value'] = round(pv['value'], kwargs['precision'])
        if kwargs['enum_strs'] == (b'OFF', b'ON'):
            pv['classes'] += ' switch'
        if pv['value'] is None: pv['value'] = '- disconnected -'
        pv['unit'] = kwargs['units'] or ''
        if pv['unit'] == 'deg C': pv['unit'] = '°C'
        if pv['unit'] == 'g/m3': pv['unit'] = 'g/m³'

# ---------- Bottle plugins / decorators ----------

def json_replace_nan():
    """
    Custom JSON decorator for Bottle routes.
    It converts a dictionary that you return to JSON before sending
    it to the browser (just like Bottle would do, but replaces any
    float('nan') value with a JSON-specs-compatible null.
    Use like this:
    @json_replace_nan()
    before the def your_func() of a route().
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                rv = func(*args, **kwargs)
            except HTTPResponse as resp:
                rv = resp
            if isinstance(rv, dict):
                #Attempt to serialize, raises exception on failure
                json_response = simplejson.dumps(rv, ignore_nan=True)
                #Set content type only if serialization successful
                response.content_type = 'application/json'
                return json_response
            elif isinstance(rv, HTTPResponse) and isinstance(rv.body, dict):
                rv.body = dumps(rv.body)
                rv.content_type = 'application/json'
            return rv
        return wrapper
    return decorator

# ---------- Bottle routes ----------

@route('/')
def index():
    redirect('/list/general_overview')

@route('/list/<page>')
@view('pv_overview.jinja2')
def list_pvs(page):
    if page not in CONFIG['pages']:
        return abort(404, 'Page not found')
    return {'config': CONFIG, 'req_page': page}

@route('/gview/<name>')
@view('gview.jinja2')
def gview(name):
    return {'config': CONFIG, 'svg': name}

@route('/api/values.json')
@json_replace_nan()
def api_values():
    return CONFIG

@route('/api/history/<name>.json')
@json_replace_nan()
def api_history(name):
    try:
        history = copy.deepcopy(HISTORY[name])
    except KeyError:
        abort(404, "PV not found")
    if len(history) != 0:
        # if the first entry is older than HISTORY_LENGTH, we 'fake' its timestamp to be HISTORY_LENGTH
        if history[0][0] < (time.time()-HISTORY_LENGTH):
            history[0][0] = time.time()-HISTORY_LENGTH
        # repeat latest value in history (to make plot lines end 'now')
        history.append([time.time(), history[-1][1]])
    for row in history:
        row[0] *= 1000.
    pv_index = CONFIG['PV_lookup'][name]
    precision = CONFIG['PVs'][pv_index]['precision']
    return {'history': history, 'precision': precision}

@route('/static/<path:path>')
def static_content(path):
    return static_file(path, root='./static/')

# ---------- main() function - managing CLI arg parsing / startup ----------

def main():
    global CONFIG, PVS, HISTORY

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
        pv['value'] = float('nan')
        pv['unit'] = None
        pv['precision'] = None
        pv['classes'] = 'disconnected'
        PVS[pv['name']] = epics.PV(pv['name'], auto_monitor=True, form='ctrl', callback=cb_value_update, connection_callback=cb_connection_change)
        CONFIG['PV_lookup'][pv['name']] = i
        HISTORY[pv['name']] = []

    run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__": main()
