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
}

CONFIG = 'log_analyzer.conf'
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
        return self.parsing(line)

    def next(self):
        return self.__next__()

    def close_file(self):
        self._log.close()

    def parsing(self, line):
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
            data = {URL: url, COUNT_PERC: self.count_perc(count), TIME_PERC: self.time_perc_sum(summ),
                    TIME_AVG: summ / count, TIME_MAX: self.time_sum_buf[url][-1],
                    TIME_MED: self.median(self.time_sum_buf[url]), TIME_SUM: summ, COUNT: count}
            yield data
        logging.info('Done')


def get_last_log(path):
    max = 0
    log_file = ''
    re_log = re.compile(RE_LOG_NAME)
    if os.path.exists(path):
        for name in os.listdir(path):
            date = re_log.search(name)
            if date:
                date = int(date.groupdict()['date'])
                if max < date:
                    max = date
                    log_file = name
    return os.path.abspath(os.path.join(path, log_file)), str(max)


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
        data = sorted((item for item in LogAnalyzer(LogParser(log, RE_LOG_LINE)).calc()),
                      key=lambda d: d[TIME_SUM], reverse=True)[:config['REPORT_SIZE']]
        try:
            with open(config['REPORT_TEMPLATE']) as template, open(report_path, 'w') as report:
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
        logging.info('End logging')


if __name__ == "__main__":
    main()