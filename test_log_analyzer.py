import unittest

from log_analyzer import LogParser
from log_analyzer import LogAnalyzer
from log_analyzer import RE_LOG_LINE


def cases(test_cases):
    def decorator(method):
        def wrapper(self):
            for test in test_cases:
                method(self, test)

        return wrapper

    return decorator


class LogParserTest(unittest.TestCase):

    def setUp(self):
        self.iterparser = iter(LogParser('./test/nginx-access-ui.log-20170630.log', RE_LOG_LINE))
        self.parser = LogParser('', RE_LOG_LINE)

    def tearDown(self):
        self.iterparser.close_file()

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
        self.assertEqual(self.parser.parsing(args[0]), args[1])

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
        item = next(self.iterparser)
        self.assertEquals(item, args)


class LogAnalyzerTest(unittest.TestCase):

    def setUp(self):
        self.analyzer = LogAnalyzer(LogParser('./test', RE_LOG_LINE))

    @cases([([0.9, 1.2, 1.23, 1.4], 1.215),
            ([0.0], 0.0),
            ([0.3], 0.3),
            ([0.30, 0.75, 0.8], 0.75)])
    def test_median(self, args):
        first = self.analyzer.median(args[0])
        self.assertAlmostEqual(first, args[1], delta=0.001)

    #def test_analyzer(self):
    #    self.analyzer.calc()




