# -*- coding: utf-8 -*-
# %load log_analyzer.py
#!/usr/bin/env python

import os
import re
import sys
import time
import gzip
import json
import logging
import argparse
import traceback
from collections import namedtuple

# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./test",
}

CONFIG = 'log_analyzer.conf'
RE_LOG_LINE = r"^.+(?:(?:GET)|(?:POST)) (?P<url>.*) HTTP/1\.[01].+(?P<request_time>\d+\.\d{3})$"
RE_LOG_NAME = r"^nginx-access-ui\.log-(?P<date>\d{8})"
PLACEHOLDER = '$table_json'
FORMAT = ('[%(asctime)s] %(levelname).1s %(message)s', '%Y.%m.%d %H:%M:%S')


class ParseError(Exception):
    pass


class LogParser:
    """Итератор по лог-файлу"""
    def __init__(self, log, re_log_line, error_threshold=0.4):
        self._log_line = re.compile(re_log_line)
        self.log = log
        self.counters = {'all': 0, 'error': 0}
        self.error_threshold = error_threshold

    def __iter__(self):
        try:
            if self.log.endswith('.gz'):
                self._log = gzip.open(self.log)
            else:
                self._log = open(self.log)
        except (IOError, OSError):
            logging.error('Error opening the file')
        else:
            logging.info('File {} is opened'.format(self._log.name))
        return self

    def __next__(self):
        if hasattr(self, '_log'):
            line = self._log.readline()
        else:
            raise StopIteration
        if not line:
            self.close_file()
            logging.info('File {} is closed'.format(self._log.name))
            raise StopIteration
        return self.parsing(line)

    def next(self):
        return self.__next__()

    def close_file(self):
        self._log.close()

    def parsing(self, line):
        self.counters['all'] += 1
        m = self._log_line.search(line)
        result = None
        if m:
            result = m.groups()
        else:
            self.counters['error'] += 1
            if self.counters['all'] * self.error_threshold <= self.counters['error'] and (
                    self.counters['all'] >= config['REPORT_SIZE']):
                self.close_file()
                raise ParseError('{} entries out of {} failed to parse'.format(
                    self.counters['error'], self.counters['all']))

        return result


class LogAnalyzer:

    def __init__(self, logiterator):
        self.logiterator = logiterator
        self.time_sum_buf = {}
        self.table = []
        self.all_time = 0.0
        self.all_count = 0

    def get_data(self):
        for item in self.logiterator:
            if item:
                self.all_count += 1
                if item[0] in self.time_sum_buf:
                    self.time_sum_buf[item[0]].append(float(item[1]))  # list of time_sum
                else:
                    self.time_sum_buf[item[0]] = [float(item[1])]
                    self.all_time += float(item[1])
        logging.info('Done')

    @staticmethod
    def median(seq):
        length = len(seq)
        if length % 2:
            med = seq[length // 2]
        else:
            med = (seq[length // 2 - 1] + seq[length // 2]) / 2.0
        return med

    def count_perc(self, count):
        return (float(count) * 100) / self.all_count

    def time_perc_sum(self, summ):
        return (summ * 100) / self.all_time

    def calc(self):
        logging.info('Reading...')
        self.get_data()
        logging.info('Data analyze...')
        for url in self.time_sum_buf:
            count = len(self.time_sum_buf[url])
            summ = sum(self.time_sum_buf[url])
            self.time_sum_buf[url].sort()
            data = {'url': url, 'count_perc': self.count_perc(count), 'time_perc': self.time_perc_sum(summ),
                    'time_avg': summ / count, 'time_max': self.time_sum_buf[url][-1],
                    'time_med': self.median(self.time_sum_buf[url]), 'time_sum': summ, 'count': count}
            yield data
        logging.info('Done')


def get_last_log(path):
    max = 0
    log_file = ''
    result = None
    re_log = re.compile(RE_LOG_NAME)
    if os.path.exists(path):
        for name in os.listdir(path):
            date = re_log.search(name)
            if date:
                date = int(date.groupdict()['date'])
                if max < date:
                    max = date
                    log_file = name
    LastLog = namedtuple('LastLog', ('path', 'year', 'month', 'day'))
    if max:
        date = str(max)
        result = LastLog(os.path.abspath(os.path.join(path, log_file)),
                         date[:4], date[4:6], date[6:])
    return result


def open_config(config):
    config = config or CONFIG
    if os.path.exists(config):
        with open(config) as f:
            try:
                return json.load(f)
            except ValueError:
                logging.error('Error reading configuration file')
                return {}
    else:
        return {}


def exept_handler(ex_type, value, tb):
    if ex_type is not ParseError:
        tb_lines = traceback.format_exception(ex_type, value, tb)
        logging.exception(''.join(tb_lines))
    else:
        logging.error(value)


def report(data, path):
    try:
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(config['REPORT_TEMPLATE']) as template, open(path, 'w') as report:
            logging.info('Reporting...')
            report.write(
                template.read().replace(
                    PLACEHOLDER, json.dumps(data)
                )
            )
            logging.info('The report {} is ready'.format(report.name))
    except (IOError, KeyError):
        logging.error('Report error')
        return
    try:
        with open(config['TS_FILE'], 'w') as f:
            f.write(str(time.time()))
    except (IOError, KeyError):
        logging.error('Timestamp not created')


def main():
    sys.excepthook = exept_handler
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', help='path to config file', default='/usr/local/etc/log_analyzer.conf')
    args = arg_parser.parse_args()
    conf = open_config(args.config)
    config.update(conf)
    logging.basicConfig(filename=config.get('SCRIPT_LOG', ''), level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    logging.info('Start logging')
    last_log = get_last_log(config['LOG_DIR'])
    if not last_log:
        logging.error('Log file not found')
        return

    report_path = os.path.join(
        config['REPORT_DIR'],
        'report-{}.{}.{}.html'.format(last_log.year, last_log.month, last_log.day)
    )

    if not os.path.exists(report_path):
        parser = LogParser(last_log.path, RE_LOG_LINE)
        analyzer = LogAnalyzer(parser)
        data = [item for item in analyzer.calc()]
        data.sort(key=lambda d: d['time_sum'], reverse=True)
        report(data[:config['REPORT_SIZE']], report_path)
        logging.info('End logging')


if __name__ == "__main__":
    main()