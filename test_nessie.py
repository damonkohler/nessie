from twisted.trial import unittest

import nessie


class MockInputFile(object):
    lines = []

    def readline(self):
        return self.lines.pop()


class MockPeer(object): pass


class TestConsoleInput(unittest.TestCase):
    def test_doReadEmptyString(self):
       ci = nessie.ConsoleInput(MockPeer())
       ci.input_file = MockInputFile()
       ci.input_file.lines = ['\n']
       self.assertEqual(ci.doRead(), None)
