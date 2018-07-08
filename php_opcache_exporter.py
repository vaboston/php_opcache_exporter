#!/usr/bin/python

import re
import time
import requests
import argparse
from pprint import pprint

import os
from sys import exit
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, REGISTRY

DEBUG = int(os.environ.get('DEBUG', '0'))

COLLECTION_TIME = Summary('php_opcache_collector_collect_seconds', 'Time spent to collect metrics from PHP OPcache')

class OpcacheCollector(object):
    # The metrics we want to export about.
    metrics = ["lastBuild", "lastCompletedBuild", "lastFailedBuild",
                "lastStableBuild", "lastSuccessfulBuild", "lastUnstableBuild",
                "lastUnsuccessfulBuild"]

    def collect(self):
        start = time.time()

        # Request data from PHP Opcache
        jobs = self._request_data()

        self._setup_empty_prometheus_metrics()

        #for job in jobs:
        #    name = job['fullName']
        #    if DEBUG:
        #        print("Found Job: {}".format(name))
        #        pprint(job)
        #    self._get_metrics(name, job)

        for status in self.metrics:
            for metric in self._prometheus_metrics[status].values():
                yield metric

        duration = time.time() - start
        COLLECTION_TIME.observe(duration)

    def _request_data(self):
        # Request exactly the information we need from Opcache
        try:
            data = json.loads(sys.argv[1])
        except:
            if DEBUG:
                print "ERROR with calling php"

        url = 'xxx/api/json'
        jobs = "[fullName,number,timestamp,duration,actions[queuingDurationMillis,totalDurationMillis," \
               "skipCount,failCount,totalCount,passCount]]"
        tree = 'jobs[fullName,url,{0}]'.format(','.join([s + jobs for s in self.metrics]))
        params = {
            'tree': tree,
        }

    def _setup_empty_prometheus_metrics(self):
        # The metrics we want to export.
        self._prometheus_metrics = {}
        for status in self.metrics:
            snake_case = re.sub('([A-Z])', '_\\1', status).lower()
            self._prometheus_metrics[status] = {
                'number':
                    GaugeMetricFamily('php_opcache_{0}'.format(snake_case),
                                      'PHP OPcache number for {0}'.format(status), labels=["jobname"]),
                'duration':
                    GaugeMetricFamily('php_opcache_{0}_duration_seconds'.format(snake_case),
                                      'PHP OPcache duration in seconds for {0}'.format(status), labels=["jobname"]),
                'timestamp':
                    GaugeMetricFamily('php_opcache_{0}_timestamp_seconds'.format(snake_case),
                                      'PHP OPcache timestamp in unixtime for {0}'.format(status), labels=["jobname"]),
                'queuingDurationMillis':
                    GaugeMetricFamily('php_opcache_{0}_queuing_duration_seconds'.format(snake_case),
                                      'PHP OPcache queuing duration in seconds for {0}'.format(status),
                                      labels=["jobname"]),
                'totalDurationMillis':
                    GaugeMetricFamily('php_opcache_{0}_total_duration_seconds'.format(snake_case),
                                      'PHP OPcache total duration in seconds for {0}'.format(status), labels=["jobname"]),
                'skipCount':
                    GaugeMetricFamily('php_opcache_{0}_skip_count'.format(snake_case),
                                      'PHP OPcache skip counts for {0}'.format(status), labels=["jobname"]),
                'failCount':
                    GaugeMetricFamily('php_opcache_{0}_fail_count'.format(snake_case),
                                      'PHP OPcache fail counts for {0}'.format(status), labels=["jobname"]),
                'totalCount':
                    GaugeMetricFamily('php_opcache_{0}_total_count'.format(snake_case),
                                      'PHP OPcache total counts for {0}'.format(status), labels=["jobname"]),
                'passCount':
                    GaugeMetricFamily('php_opcache_{0}_pass_count'.format(snake_case),
                                      'PHP OPcache pass counts for {0}'.format(status), labels=["jobname"]),
            }

    def _get_metrics(self, name, job):
        for status in self.statuses:
            if status in job.keys():
                status_data = job[status] or {}
                self._add_data_to_prometheus_structure(status, status_data, job, name)

    def _add_data_to_prometheus_structure(self, status, status_data, job, name):
        # If there's a null result, we want to pass.
        if status_data.get('duration', 0):
            self._prometheus_metrics[status]['duration'].add_metric([name], status_data.get('duration') / 1000.0)
        if status_data.get('timestamp', 0):
            self._prometheus_metrics[status]['timestamp'].add_metric([name], status_data.get('timestamp') / 1000.0)
        if status_data.get('number', 0):
            self._prometheus_metrics[status]['number'].add_metric([name], status_data.get('number'))
        actions_metrics = status_data.get('actions', [{}])
        for metric in actions_metrics:
            if metric.get('queuingDurationMillis', False):
                self._prometheus_metrics[status]['queuingDurationMillis'].add_metric([name], metric.get('queuingDurationMillis') / 1000.0)
            if metric.get('totalDurationMillis', False):
                self._prometheus_metrics[status]['totalDurationMillis'].add_metric([name], metric.get('totalDurationMillis') / 1000.0)
            if metric.get('skipCount', False):
                self._prometheus_metrics[status]['skipCount'].add_metric([name], metric.get('skipCount'))
            if metric.get('failCount', False):
                self._prometheus_metrics[status]['failCount'].add_metric([name], metric.get('failCount'))
            if metric.get('totalCount', False):
                self._prometheus_metrics[status]['totalCount'].add_metric([name], metric.get('totalCount'))
                # Calculate passCount by subtracting fails and skips from totalCount
                passcount = metric.get('totalCount') - metric.get('failCount') - metric.get('skipCount')
                self._prometheus_metrics[status]['passCount'].add_metric([name], passcount)


def parse_args():
    parser = argparse.ArgumentParser(
        description='php_opcache_exporter args'
    )
    parser.add_argument(
        '-p', '--port',
        metavar='port',
        required=False,
        type=int,
        help='Listen to this port',
        default=int(os.environ.get('VIRTUAL_PORT', '9462'))
    )
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        port = int(args.port)
        REGISTRY.register(OpcacheCollector())
        start_http_server(port)
        print("Polling... Serving at port: {}".format(args.port))
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(" Interrupted")
        exit(0)


if __name__ == "__main__":
    main()