from twisted.trial import unittest

import nessie
import mocks


class TestConsoleInput(unittest.TestCase):
    def test_doReadEmptyString(self):
       ci = nessie.ConsoleInput(mocks.MockPeer())
       mf = mocks.MockFile()
       mf.read_lines = ['\n']
       ci.input_file = mf
       self.assertEqual(ci.doRead(), None)
