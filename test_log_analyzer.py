import os
import unittest

import log_analyzer
from log_analyzer import log_parser
from log_analyzer import LogAnalyzer
from log_analyzer import RE_LOG_LINE
from log_analyzer import log_generator


def cases(test_cases):
    def decorator(method):
        def wrapper(self):
            for test in test_cases:
                method(self, test)

        return wrapper

    return decorator


class LogParserTest(unittest.TestCase):

    def setUp(self):
        self.log_generator = log_generator('./test/nginx-access-ui.log-20170630.log', log_parser, RE_LOG_LINE)

    def tearDown(self):
        self.log_generator.close()

    @cases([('1.200.76.128 f032b48fb33e1e692  - [29/Jun/2017:03:51:09 +0300] "GET /api/1/campaigns/?id=7391355 HTTP/1.1'
             '" 200 704 "-" "-" "-" "1498697469-4102637017-4709-9929537" "-" 0.145',
             ('/api/1/campaigns/?id=7391355', '0.145')),
            ('1.168.65.96 -  - [29/Jun/2017:03:51:09 +0300] "GET /api/v2/internal/banner/24295823/info HTTP/1.1" 200'
             ' 389 "-" "-" "-" "1498697469-2539198130-4709-9929538" "89f7f1be37d" 0.063',
             ('/api/v2/internal/banner/24295823/info', '0.063')),
            ('1.169.137.128 -  - [29/Jun/2017:03:51:09 +0300] "GET /api/v2/group/7920452/banners HTTP/1.1" 200 1095 "-"'
             ' "Configovod" "-" "1498697469-2118016444-4709-9929515" "712e90144abee9" 0.665',
             ('/api/v2/group/7920452/banners', '0.665')),
            ('1.168.65.96 -  - [29/Jun/2017:03:51:11 +0300] "GET /api/v2/internal/banner/24287677/info HTTP/1.0" 200'
             ' 400 "-" "-" "-" "1498697471-2539198130-4709-9929574" "89f7f1be37d" 0.098',
             ('/api/v2/internal/banner/24287677/info', '0.098')),
            ('1.169.137.128 -  - [29/Jun/2017:03:51:11 +0300] "GET /api/v2/group/6404923/banners HTTP/1.1" 200 982 "-"'
             ' "Configovod" "-" "1498697471-2118016444-4709-9929568" "712e90144abee9" 0.524',
             ('/api/v2/group/6404923/banners', '0.524')),
            ('1.168.65.96 -  - [29/Jun/2017:03:51:11 +0300] "GET /api/v2/internal/banner/24284366/info HTTP/1.0" 200'
             ' 371 "-" "-" "-" "1498697471-2539198130-4709-9929575" "89f7f1be37d" 0.057',
             ('/api/v2/internal/banner/24284366/info', '0.057')),
            ('1.200.76.128 f032b48fb33e1e692  - [29/Jun/2017:03:51:11 +0300] "GET /api/1/campaigns/?id=7854260'
             ' HTTP/1.0" 200 615 "-" "-" "-" "1498697471-4102637017-4709-9929573" "-" 0.213',
             ('/api/1/campaigns/?id=7854260', '0.213'))])
    def test_parsing(self, args):
        self.assertEqual(log_parser(RE_LOG_LINE, args[0]), args[1])

    @cases([('/api/v2/banner/24824230', '0.143'),
             ('/export/appinstall_raw/2017-06-30/', '0.001'),
             ('/api/v2/group/6646605/statistic/sites/?date_type=day&date_from=2017-06-29&date_to=2017-06-29', '0.070'),
             ('/api/v2/banner/26736849', '1.360'),
             ('/api/1/banners/?campaign=434094', '0.169'),
             ('/api/v2/banner/22211801/statistic/?date_from=2017-06-29&date_to=2017-06-29', '0.100'),
             ('/api/v2/banner/26736214', '1.417'),
             ('/api/v2/banner/227223', '0.163'),
             ('/api/v2/internal/revenue_share/service/276/partner/545765/statistic/v2?date_from='
              '2017-06-23&date_to=2017-06-29&date_type=day', '0.156'),
             ('/api/1/banners/?campaign=451660', '0.163'),
             ('/api/v2/slot/16128/groups', '0.118'),
             ('/export/appinstall_raw/2017-06-29/', '0.003')])
    def test_file_iteration(self, args):
        item = next(self.log_generator)
        self.assertEquals(item, args)


class LogAnalyzerTest(unittest.TestCase):

    def setUp(self):
        self.analyzer = LogAnalyzer(None)
        self.log_generator1 = log_generator('./test/nginx-access-ui.log-20170630.log', log_parser, RE_LOG_LINE)
        self.log_generator2 = log_generator('./test/nginx-access-ui.log-20170630.log', log_parser, RE_LOG_LINE)
        self.calc_generator = LogAnalyzer(self.log_generator1).calc()
        self.true_analyzer = LogAnalyzer(self.log_generator2)
        self.true_analyzer.get_data()

    def tearDown(self):
        self.log_generator1.close()
        self.log_generator2.close()
        self.calc_generator.close()

    @cases([([0.9, 1.2, 1.23, 1.4], 1.215),
            ([0.0], 0.0),
            ([0.3], 0.3),
            ([0.30, 0.75, 0.8], 0.75)])
    def test_median(self, args):
        first = self.analyzer.median(args[0])
        self.assertAlmostEqual(first, args[1], delta=0.001)

    @cases([{'count': 2, 'time_avg': 0.021, 'time_max': 0.021, 'time_sum': 0.042, 'url': '/api/v2/test/auth/',
             'time_med': 0.021, 'time_perc': 0.021902035324854106, 'count_perc': 0.5813953488372093},
            {'count': 24, 'time_avg': 0.0027083333333333347, 'time_max': 0.006, 'time_sum': 0.06500000000000003,
             'url': '/export/appinstall_raw/2017-06-29/', 'time_med': 0.003, 'time_perc': 0.03389600705036946,
             'count_perc': 6.976744186046512},
            {'count': 25, 'time_avg': 0.0009200000000000006, 'time_max': 0.001, 'time_sum': 0.023000000000000013,
             'url': '/export/appinstall_raw/2017-06-30/', 'time_med': 0.001, 'time_perc': 0.011993971725515348,
             'count_perc': 7.267441860465116}])
    def test_calculation(self, kwargs):
        url = kwargs['url']
        count = len(self.true_analyzer.time_sum_buf[url])
        time_sum = sum(self.true_analyzer.time_sum_buf[url])
        self.true_analyzer.time_sum_buf[url].sort()
        count_perc = self.true_analyzer.count_perc(count)
        time_perc = self.true_analyzer.time_perc_sum(time_sum)
        time_avg = time_sum / count
        time_max = self.true_analyzer.time_sum_buf[url][-1]
        time_med = self.true_analyzer.median(self.true_analyzer.time_sum_buf[url])

        self.assertEqual(kwargs['count'], count)
        self.assertEqual(kwargs['url'], url)
        self.assertAlmostEqual(kwargs['time_avg'], time_avg, delta=0.001)
        self.assertAlmostEqual(kwargs['time_max'], time_max, delta=0.001)
        self.assertAlmostEqual(kwargs['time_sum'], time_sum, delta=0.001)
        self.assertAlmostEqual(kwargs['time_med'], time_med, delta=0.001)
        self.assertAlmostEqual(kwargs['time_perc'], time_perc, delta=0.001)
        self.assertAlmostEqual(kwargs['count_perc'], count_perc, delta=0.001)

    @cases([{'count': 1, 'time_avg': 0.145, 'time_max': 0.145, 'time_sum': 0.145, 'url': '/api/v2/banner/1717161',
             'time_med': 0.145, 'time_perc': 0.07561416957390106, 'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 0.183, 'time_max': 0.183, 'time_sum': 0.183, 'url': '/api/1/campaigns/?id=7952462',
             'time_med': 0.183, 'time_perc': 0.0954302967725786, 'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 0.386, 'time_max': 0.386, 'time_sum': 0.386,
             'url': '/api/v2/group/7843268/banners', 'time_med': 0.386, 'time_perc': 0.2012901341760401,
             'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 0.142, 'time_max': 0.142, 'time_sum': 0.142, 'url': '/api/v2/banner/16168711',
             'time_med': 0.142, 'time_perc': 0.07404973847926863, 'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 0.068, 'time_max': 0.068, 'time_sum': 0.068,
             'url': '/api/v2/banner/26624919/statistic/?date_from=2017-06-29&date_to=2017-06-29', 'time_med': 0.068,
             'time_perc': 0.03546043814500188, 'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 0.587, 'time_max': 0.587, 'time_sum': 0.587,
             'url': '/api/v2/group/7861864/banners', 'time_med': 0.587, 'time_perc': 0.3061070175164133,
             'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 0.061, 'time_max': 0.061, 'time_sum': 0.061,
             'url': '/api/v2/group/6812420/statistic/sites/?date_type=day&date_from=2017-06-29&date_to=2017-06-29',
             'time_med': 0.061, 'time_perc': 0.03181009892419286, 'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 1.991, 'time_max': 1.991, 'time_sum': 1.991, 'url': '/api/v2/banner/21542368',
             'time_med': 1.991, 'time_perc': 1.0382607698043935, 'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 0.178, 'time_max': 0.178, 'time_sum': 0.178,
             'url': '/api/v2/internal/revenue_share/service/276/partner/1114631/statistic/v2?date_from=2017-06-23'
                    '&date_to=2017-06-29&date_type=day', 'time_med': 0.178, 'time_perc': 0.09282291161485787,
             'count_perc': 0.29069767441860467},
            {'count': 1, 'time_avg': 0.096, 'time_max': 0.096, 'time_sum': 0.096,
             'url': '/api/v2/group/7181748/statistic/sites/?date_type=day&date_from=2017-06-29&date_to=2017-06-29',
             'time_med': 0.096, 'time_perc': 0.050061795028237946, 'count_perc': 0.29069767441860467}])
    def test_analyzer(self, kwargs):
        data = next(self.calc_generator)
        self.assertEqual(data['count'], kwargs['count'])
        self.assertEqual(data['url'], kwargs['url'])
        self.assertAlmostEqual(data['time_avg'], kwargs['time_avg'], delta=0.001)
        self.assertAlmostEqual(data['time_max'], kwargs['time_max'], delta=0.001)
        self.assertAlmostEqual(data['time_sum'], kwargs['time_sum'], delta=0.001)
        self.assertAlmostEqual(data['time_med'], kwargs['time_med'], delta=0.001)
        self.assertAlmostEqual(data['time_perc'], kwargs['time_perc'], delta=0.001)
        self.assertAlmostEqual(data['count_perc'], kwargs['count_perc'], delta=0.001)

    def test_get_last_log(self):
        path = log_analyzer.get_last_log('./test')[0]
        name = path.split(os.path.sep)[-1]
        self.assertEqual(name, 'nginx-access-ui.log-20170630.log')

    @cases([('unknown', {}),
            ('log_analyzer.conf', {"REPORT_TEMPLATE": "./report.html",
                                   "TS_FILE": "/var/tmp/log_analyzer.ts"})
            ])
    def test_open_config(self, args):
        self.assertEqual(log_analyzer.open_config(args[0]), args[1])
