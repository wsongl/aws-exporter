#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# import lib
from flask import Flask
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware


def create_app():
    app = Flask(__name__)

    app_dispatch = DispatcherMiddleware(app, {
        '/metrics': make_wsgi_app()
    })
    return app_dispatch
