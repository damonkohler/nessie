from twisted.trial import unittest

import pb2pb

class TestPeer(unittest.TestCase):
    pass


class TestProxy(unittest.TestCase):
    pass


class TestPeerProxy(unittest.TestCase):
    pass


class TestConsoleInput(unittest.TestCase):
    pass


class MockFile(object):
    def __init__(self, results):
        self.results = results

    def write(self, msg):
        self.results.append(msg)


class TestChat(unittest.TestCase):
    def test_remote_Say(self):
        msg = 'Hello World!'
        results = []
        pb2pb.Chat.chat_file = MockFile(results)
        chat = pb2pb.Chat()
        chat.remote_Say(msg)
        self.assertEqual([chat.chat_format % msg], results)
        
    def test_SayToFile(self):
        msg = 'Hello World!'
        results = []
        chat_file = MockFile(results)
        chat = pb2pb.Chat()
        chat._SayToFile(msg, chat_file)
        self.assertEqual([chat.chat_format % msg], results)
