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
        self.parser = iter(LogParser('./test/nginx-access-ui.log-20170630.log', RE_LOG_LINE))

    def tearDown(self):
        self.parser.close_file()

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
    def test_parsing(self, args):
        item = next(self.parser)
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




