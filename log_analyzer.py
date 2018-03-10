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
from datetime import datetime
from collections import namedtuple
from collections import defaultdict

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
RE_LOG_LINE = r"^.+(?:(?:GET)|(?:POST)|(?:HEAD)|(?:PUT)) (?P<url>.*) HTTP/1\.[01].+(?P<request_time>\d+\.\d{3})$"
RE_LOG_NAME = r"^nginx-access-ui\.log-(?P<date>\d{8})(?:\.(?:(?:gz)|(?:log)|(?:txt)))?$"
PLACEHOLDER = '$table_json'
FORMAT = ('[%(asctime)s] %(levelname).1s %(message)s', '%Y.%m.%d %H:%M:%S')


def log_generator(log, parser=None, re_log_str=None, error_threshold=0.4):
    """ Генератор, обеспечивающий построковое чтение лог-файла.
        В качестве аргументов можно передать парсер, строку регулярного выражения
        и порог ошибок парсинга.
    """
    error_threshold = error_threshold
    _all = 0
    errors = 0
    with gzip.open(log) if log.endswith('.gz') else open(log) as log_file:
        for line in log_file:
            if line:
                if parser and re_log_str:
                    _all += 1
                    line = parser(re_log_str, line)
                    if not line:
                        errors += 1
                yield line
    if _all * error_threshold < errors and (
            _all >= config['REPORT_SIZE']):
        # превышен порог ошибок парсинга
        logging.error('{} entries out of {} failed to parse'.format(errors, _all))


def log_parser(re_log_str, line):
    """Парсер логов"""
    re_log_line = re.compile(re_log_str)
    re_result = re_log_line.search(line)
    if re_result:
        return re_result.groups()
    else:
        return None


class LogAnalyzer:

    def __init__(self, logiterator):
        self.logiterator = logiterator
        self.time_sum_buf = defaultdict(list)
        self.table = []
        self.all_time = 0.0
        self.all_count = 0

    def get_data(self):
        for item in self.logiterator:
            if item:
                self.all_count += 1
                self.time_sum_buf[item[0]].append(float(item[1]))
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
    if max:
        LastLog = namedtuple('LastLog', ('path', 'date'))
        date = str(max)
        dt = datetime.strptime(date, '%Y%m%d')
        result = LastLog(os.path.abspath(os.path.join(path, log_file)), dt)
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


def write_ts():
    try:
        with open(config['TS_FILE'], 'w') as f:
            f.write(str(time.time()))
    except (IOError, KeyError):
        logging.error('Timestamp not created')


def main():
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
        logging.info('Log file not found')
        return

    report_path = os.path.join(
        config['REPORT_DIR'],
        'report-{}.html'.format(last_log.date.strftime('%Y.%m.%d'))
    )

    if not os.path.exists(report_path):
        if not os.path.exists(config['REPORT_DIR']):
            os.makedirs(config['REPORT_DIR'])
        analyzer = LogAnalyzer(log_generator(last_log.path, log_parser, RE_LOG_LINE))
        data = [item for item in analyzer.calc()]
        data = sorted(data, key=lambda d: d['time_sum'], reverse=True)
        report(data[:config['REPORT_SIZE']], report_path)
        write_ts()
        logging.info('End logging')


if __name__ == "__main__":
    try:
        main()
    except:
        tb_lines = traceback.format_exception(*sys.exc_info())
        logging.exception(''.join(tb_lines))