# -*- coding: utf-8 -*-
# %load log_analyzer.py
#!/usr/bin/env python

import os
import re
import time
import gzip
import json
import argparse
import logging

# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./test",
    "REPORT_TEMPLATE": "./report.html",
    "TS_FILE": "/var/tmp/log_analyzer.ts"
}

_CONFIG = 'log_analyzer.conf'
RE_LOG_LINE = r"^.+(?:(?:GET)|(?:POST)) (?P<url>.*) HTTP/1\.[01].+(?P<request_time>\d+\.\d{3})$"
RE_LOG_NAME = r"^nginx-access-ui\.log-(?P<date>\d{8})"
PLACEHOLDER = '$table_json'
FORMAT = ('[%(asctime)s] %(levelname).1s %(message)s', '%Y.%m.%d %H:%M:%S')
URL = 'url'
TIME_SUM = 'time_sum'
COUNT = 'count'
COUNT_PERC = 'count_perc'
TIME_PERC = 'time_perc'
TIME_AVG = 'time_avg'
TIME_MAX = 'time_max'
TIME_MED = 'time_med'
COLUMN = (URL, TIME_SUM, COUNT, COUNT_PERC, TIME_PERC, TIME_AVG, TIME_MAX, TIME_MED)


class LogParser:
    """Итератор по лог-файлу"""
    def __init__(self, log, re_log_line):
        self._log_line = re.compile(re_log_line)
        self.log = log

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
        return self._parse_line(line)

    def next(self):
        return self.__next__()

    def close_file(self):
        self._log.close()

    def _parse_line(self, line):
        m = self._log_line.search(line)
        res = []
        if m:
            res = m.groups()
        return res


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
        # инициализация таблицы
        for key in self.time_sum_buf:
            self.table.append(
                dict(
                    zip(COLUMN,
                        (key, sum(self.time_sum_buf[key]), len(self.time_sum_buf[key]), 0.0, 0.0, 0.0, 0.0, 0.0)
                        )
                )
            )

    @staticmethod
    def median(seq):
        length = len(seq)
        if length % 2:
            med = seq[length // 2]
        else:
            med = (seq[length // 2 - 1] + seq[length // 2]) / 2.0
        return med

    def calc(self):
        logging.info('Reading...')
        self.get_data()
        logging.info('Data analyze...')
        for d in self.table:
            d[COUNT_PERC] = (float(d[COUNT]) * 100) / self.all_count
            d[TIME_PERC] = (d[TIME_SUM] * 100) / self.all_time
            d[TIME_AVG] = d[TIME_SUM] / d[COUNT]
            self.time_sum_buf[d[URL]].sort()
            d[TIME_MAX] = self.time_sum_buf[d[URL]][-1]
            d[TIME_MED] = self.median(self.time_sum_buf[d[URL]])
        logging.info('done')
        return self.table


def get_last_log(path):
    max = 0
    log_file = ''
    re_log = re.compile(RE_LOG_NAME)
    if os.path.exists(path):
        for name in os.listdir(path):
            date = re_log.search(name)
            if name:
                try:
                    date = int(date.groupdict()['date'])
                    if max < date:
                        max = date
                        log_file = name
                except ValueError:
                    continue
    return os.path.abspath(os.path.join(path, log_file)), str(max)


def open_config(config):
    config = config or _CONFIG
    if os.path.exists(config):
        with open(config) as f:
            try:
                return json.load(f)
            except ValueError:
                logging.error('Error reading configuration file')
                return {}
    else:
        return {}


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', help='path to config file', default='/usr/local/etc/log_nalyzer.conf')
    args = arg_parser.parse_args()
    conf = open_config(args.config)
    config.update(conf)
    logging.basicConfig(filename=config.get('SCRIPT_LOG', ''), level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    logging.info('Start logging')
    log, date = get_last_log(config['LOG_DIR'])
    if log:
        year, month, day = date[:4], date[4:6], date[6:]
    else:
        logging.error('Log file not found')
        return

    report_path = os.path.join(
        config['REPORT_DIR'],
        'report-{}.{}.{}.html'.format(year, month, day)
    )

    if not os.path.exists(report_path):
        data = LogAnalyzer(LogParser(log, RE_LOG_LINE)).calc()

        logging.info('Preparation for the report...')
        data.sort(key=lambda d: d[TIME_SUM], reverse=True)
        logging.info('Done')
        try:
            with open(config['REPORT_TEMPLATE']) as template, open(report_path, 'w') as report:
                logging.info('Reporting...')
                report.write(
                    template.read().replace(
                        PLACEHOLDER, json.dumps(data[:config['REPORT_SIZE']])
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
        logging.info('End logging')


if __name__ == "__main__":
    main()