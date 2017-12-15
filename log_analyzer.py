# %load log_analyzer.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import gzip
import json
import argparse
import logging
import logging.handlers

# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}

_CONFIG = 'log_analyzer.conf'
RE_LOG_LINE = r"^.+(?:(?:GET)|(?:POST)) (?P<url>.*) HTTP/1\.1.+(?P<request_time>\d+\.\d{3})$"
RE_LOG_NAME = r"^nginx-access-ui\.log-(?P<date>\d{8})"
PLACEHOLDER = '$table_json'
FORMAT = ('[%(asctime)s] %(levelname).1s %(message)s', '%Y.%m.%d %H:%M:%S')


class LogParser:
    """Итератор по лог-файлу"""
    def __init__(self, log, re_log_line, logger):
        self._log_line = re.compile(re_log_line)
        self.log = log
        self.logger = logger

    def __iter__(self):
        try:
            if self.log.endswith('.gz'):
                self.f = gzip.open(self.log)
            else:
                self.f = open(self.log)
        except (IOError, OSError):
            self.logger.exception('open file error')
        else:
            self.logger.info('file {} is open'.format(self.f.name))
        return self

    def __next__(self):
        if hasattr(self, 'f'):
            line = self.f.readline()
        else:
            raise StopIteration
        if not line:
            self.f.close()
            self.logger.info('eof. file {} is closed'.format(self.f.name))
            raise StopIteration
        return self._parse_line(line)

    def _parse_line(self, line):
        if isinstance(line, bytes):  # for python3
            line = line.decode()
        m = self._log_line.search(line)
        res = []
        if m:
            res = m.groups()
        return res


class LogAnalyzer:

    _COLUMN = ('url', 'time_sum', 'count', 'count_perc', 'time_perc', 'time_avg', 'time_max', 'time_med')

    def __init__(self, logiterator, logger):
        self.logiterator = logiterator
        self.time_sum_buf = {}
        self.table = []
        self.all_time = 0.0
        self.logger = logger

    def _collect(self):
        for i, item in enumerate(self.logiterator):
            if i == 0:
                self.logger.info('reading...')
            try:
                if item:
                    if item[0] in self.time_sum_buf:
                        self.time_sum_buf[item[0]][0] += float(item[1])       # sum of time_sum
                        self.time_sum_buf[item[0]][1].append(float(item[1]))  # list of time_sum
                    else:
                        self.time_sum_buf[item[0]] = [float(item[1]), [float(item[1])]]
                        self.all_time += float(item[1])
            except:
                self.logger.exception('something went wrong on the {} line of the file reading'.format(i))
                continue
        self.logger.info('done')

        for key in self.time_sum_buf:
            self.table.append(
                dict(
                    zip(self.__class__._COLUMN,
                        (key, self.time_sum_buf[key][0], len(self.time_sum_buf[key][1]), 0.0, 0.0, 0.0, 0.0, 0.0)
                        )
                )
            )

    @staticmethod
    def _median(seq):
        length = len(seq)
        if length % 2:
            med = seq[length // 2]
        else:
            med = (seq[length // 2 - 1] + seq[length // 2]) / 2.0
        return med

    def calc(self):
        self._collect()
        self.logger.info('data analyze...')
        for d in self.table:
            d['count_perc'] = (d['count'] * 100) / len(self.table)
            d['time_perc'] = (d['time_sum'] * 100) / self.all_time
            d['time_avg'] = d['time_sum'] / d['count']
            self.time_sum_buf[d['url']][1].sort()
            d['time_max'] = self.time_sum_buf[d['url']][1][-1]
            d['time_med'] = self._median(self.time_sum_buf[d['url']][1])
        self.logger.info('done')

        return self.table


class LastLogFile:
    def __init__(self, re_log):
        self._log = re.compile(re_log)

    def _find_last_file(self, file_list):
        max = 0
        last_file = ''
        for name in file_list:
            s = self._log.search(name)
            if s:
                try:
                    cur = int(s.groupdict()['date'])
                    if max < cur:
                        max = cur
                        last_file = name
                except ValueError:
                    continue
        return last_file, str(max)

    def find(self, log_dir):
        return self._find_last_file(os.listdir(log_dir))


def open_config(config):
    config = config or _CONFIG
    with open(config) as f:
        return json.load(f)


def get_logger(name, file='', format=FORMAT, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if file:
        handler = logging.handlers.RotatingFileHandler(file, maxBytes=8192, backupCount=10)
    else:
        handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(*format))
    logger.addHandler(handler)
    return logger


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', help='path to config file')
    args = arg_parser.parse_args()
    conf = open_config(args.config)
    logger = get_logger(__name__, conf.get('SCRIPT_LOG', ''))
    logger.info('start logging')
    log, date = LastLogFile(RE_LOG_NAME).find(conf['LOG_DIR'])

    report_path = os.path.join(
        conf['REPORT_DIR'],
        conf['REPORT_TEMPLATE'] + '-' + date[:3] + '.' + date[3:5] + '.' + date[5:]
    )

    if not os.path.exists(report_path):
        data = LogAnalyzer(
            LogParser(
                log, RE_LOG_LINE, logger
            ),
            logger
        ).calc()

        logger.info('preparation for the report...')
        data.sort(key=lambda d: d['time_sum'], reverse=True)
        logger.info('done')
        try:
            with open(conf['REPORT_TEMPLATE']) as template, open(report_path, 'w') as report:
                logger.info('reporting...')
                report.write(
                    template.read().replace(
                        PLACEHOLDER ,data[:conf['REPORT_SIZE']]
                    )
                )
                logger.info('the report {} is ready'.format(report.name))
        except IOError:
            logger.exception('report error')
        else:
            try:
                with open(conf['TS_FILE'], 'w') as f:
                    f.write(str(time.time()))
            except IOError:
                logger.exception('timestamp not created')

        logger.info('end logging')


if __name__ == "__main__":
    main()