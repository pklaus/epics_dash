#!/usr/bin/env python

import json, threading, time, copy, math

import simplejson
import epics
from bottle import Bottle, run, static_file, redirect, abort, response, HTTPResponse, server_names
from bottle import jinja2_view as view
from requestlogger import WSGILogger, ApacheFormatter
from logging.handlers import TimedRotatingFileHandler


try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

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
    if len(HISTORY[pv_name]) > 0 and math.isnan(value):
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
        for prop in ('value', 'char_value'):
            if HAS_NUMPY and isinstance(kwargs[prop], np.ndarray):
                kwargs[prop] = kwargs[prop].tolist()
        class_map = {
          epics.NO_ALARM :      "",
          epics.MINOR_ALARM :   "minor_alarm",
          epics.MAJOR_ALARM :   "major_alarm",
          epics.INVALID_ALARM : "invalid_alarm",
          None : "disconnected",
        }
        pv['classes'] = class_map[kwargs['severity']]
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
        # DRVL / DRVH
        if kwargs['upper_ctrl_limit'] != kwargs['lower_ctrl_limit']:
            pv['upper_ctrl_limit'] = kwargs['upper_ctrl_limit']
            pv['lower_ctrl_limit'] = kwargs['lower_ctrl_limit']
        else:
            pv['upper_ctrl_limit'] = float('nan')
            pv['lower_ctrl_limit'] = float('nan')
        # HOPR / LOPR
        if kwargs['upper_disp_limit'] != kwargs['lower_disp_limit']:
            pv['upper_disp_limit'] = kwargs['upper_disp_limit']
            pv['lower_disp_limit'] = kwargs['lower_disp_limit']
        else:
            pv['upper_disp_limit'] = float('nan')
            pv['lower_disp_limit'] = float('nan')
        # HIHI / LOLO
        if kwargs['upper_alarm_limit'] != kwargs['lower_alarm_limit']:
            pv['upper_alarm_limit'] = kwargs['upper_alarm_limit']
            pv['lower_alarm_limit'] = kwargs['lower_alarm_limit']
        else:
            pv['upper_alarm_limit'] = float('nan')
            pv['lower_alarm_limit'] = float('nan')
        # HIGH / LOW
        if kwargs['upper_warning_limit'] != kwargs['lower_warning_limit']:
            pv['upper_warning_limit'] = kwargs['upper_warning_limit']
            pv['lower_warning_limit'] = kwargs['lower_warning_limit']
        else:
            pv['upper_warning_limit'] = float('nan')
            pv['lower_warning_limit'] = float('nan')
        # PREC
        pv['precision'] = kwargs['precision']
        #if type(kwargs['precision']) == int and kwargs['precision'] > 0 and ('double' in kwargs['type'] or 'float' in kwargs['type']):
        #    pv['value'] = round(pv['value'], kwargs['precision'])
        if kwargs['enum_strs'] == (b'OFF', b'ON'):
            pv['classes'] += ' switch'
        if pv['value'] is None: pv['value'] = '- disconnected -'
        # EGU
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

app = Bottle()

@app.route('/')
def index():
    redirect('/list_bs/general_overview')

@app.route('/pv/<pv_name>')
@view('pv_details_bootstrap.jinja2')
def pv_details(pv_name):
    property_name_mapping = {
      'name': 'Process Variable Name',
      'alias': 'Alias',
      'descr': 'Description',
      'value': 'Value',
      'unit': 'Unit of Value',
      'precision': 'Precision of Value',
      'classes': 'Classes / Tags',
      'num_value': 'Numerical Value',
      'char_value': 'String Representation of Value',
      'upper_ctrl_limit': 'Upper Control Range Limit',
      'lower_ctrl_limit': 'Lower Control Range Limit',
      'upper_disp_limit': 'Upper Operator Display Limit',
      'lower_disp_limit': 'Lower Operator Display Limit',
      'upper_alarm_limit': 'Upper Alarm Limit',
      'lower_alarm_limit': 'Lower Alarm Limit',
      'upper_warning_limit': 'Upper Warning Limit',
      'lower_warning_limit': 'Lower Warning Limit',
    }
    epics_ioc_terminology = {
      'value': 'VAL',
      'unit': 'EGU',
      'precision': 'PREC',
      'upper_ctrl_limit': 'DRVH',
      'lower_ctrl_limit': 'DRVL',
      'upper_disp_limit': 'HOPR',
      'lower_disp_limit': 'LOPR',
      'upper_alarm_limit': 'HIHI',
      'lower_alarm_limit': 'LOLO',
      'upper_warning_limit': 'HIGH',
      'lower_warning_limit': 'LOW',
    }
    return {'pv_name': pv_name, 'config': CONFIG, 'property_name_mapping': property_name_mapping, 'epics_ioc_terminology': epics_ioc_terminology}

@app.route('/list_bs/<page>')
@view('pv_overview_bootstrap.jinja2')
def list_pvs_bs(page):
    if page not in CONFIG['pages']:
        return abort(404, 'Page not found')
    return {'config': CONFIG, 'req_page': page}

@app.route('/list/<page>')
@view('pv_overview.jinja2')
def list_pvs(page):
    if page not in CONFIG['pages']:
        return abort(404, 'Page not found')
    return {'config': CONFIG, 'req_page': page}

@app.route('/gview/<name>')
@view('gview.jinja2')
def gview(name):
    try:
        svg = CONFIG['pages'][name]['gview']
    except KeyError:
        return abort(404, 'Page not found')
    return {'config': CONFIG, 'req_page': name, 'svg': svg}

@app.route('/api/current_state')
@json_replace_nan()
def api_values():
    return CONFIG

@app.route('/api/history/<name>')
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
    pv = CONFIG['PVs'][pv_index]
    precision = pv['precision']
    ret_dict = {'history': history}
    ret_dict.update(pv)
    return ret_dict

@app.route('/static/<path:path>')
def static_content(path):
    return static_file(path, root='./static/')

# ---------- main() function - managing CLI arg parsing / startup ----------

def main():
    global CONFIG, PVS, HISTORY, app

    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0',
          help='The host (IP address) the web server should listen on.')
    parser.add_argument('--port', default=4913,
          help='The port the web server should listen on.')
    parser.add_argument('--config', '-c', required=True,
          help='The config file with the definition of process variables and EPICS hosts.')
    parser.add_argument('--server', default='wsgiref',
          help='Server engine to run the application. Valid choices: ' + ', '.join(server_names) + '. '
               'The default is wsgiref (try bjoern or paste for high performance and read https://goo.gl/SmPFZb).')
    parser.add_argument('--logfile',
          help='If provided, the server will log requests to this file in "Apache format".')
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

    if args.logfile:
        handlers = [ TimedRotatingFileHandler(args.logfile, when='W0', interval=1) , ]
        app = WSGILogger(app, handlers, ApacheFormatter())

    run(app, host=args.host, port=args.port, debug=args.debug, server=args.server)

if __name__ == "__main__": main()
