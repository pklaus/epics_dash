#!/usr/bin/env python

from bottle import route, run, static_file
from bottle import jinja2_view as view

@route('/')
@view('pv_overview.jinja2')
def index():
    return {}

@route('/static/<path:path>')
def static_content(path):
    return static_file(path, root='./static/')

run(host='', port=8080)
