#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import signal
import logging
import argparse
import sys
import yaml
import os

from wsgiref.simple_server import make_server
from prometheus_client import REGISTRY

from web import create_app
from cloud.aws import AWS
from collector.collector import AwsCollector


def signal_handler():
    logging.warning('stop alert service.')
    sys.exit(1)


def main():
    # signal: stop service
    signal.signal(signal.SIGTERM, signal_handler)

    # create exporter log
    if not os.path.exists(r"logs"):
        os.mkdir("logs")

    # set log
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", filename="logs/aws-exporter.log")

    # parse parm
    parser = argparse.ArgumentParser(description='aws exporter args')
    parser.add_argument("-c", "--config", default="default.yml", help="the config file of exporter")
    parser.add_argument('-p', '--port', default=9091, help='the port of aws exporter service')
    args = parser.parse_args()

    # read config file
    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    aws_client = AWS(**config)

    # collector
    collector = AwsCollector(aws_client)
    REGISTRY.register(collector)

    # web
    logging.info('start running aws exporter service.')
    print('start running aws exporter service.')
    app = create_app()
    httpd = make_server('', int(args.port), app)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
