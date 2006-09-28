from twisted.trial import unittest

import pb2pb


class MockRemotePeer(object):
    def __init__(self):
        self.broker = MockBroker()


class MockBroker(object):
    disconnected = 0


class TestPeer(unittest.TestCase):
    def _GetPeerForTesting(self):
        p = pb2pb.Peer()
        p.peers = {0: [], 1: [], 2: []}
        for uuid, routes in p.peers.iteritems():
            for i in range(len(p.peers)):
                p.peers[uuid].append(MockRemotePeer())
            p.peers[uuid][uuid].broker.disconnected = 1
        return p

    def testIterPeers(self):
        p = self._GetPeerForTesting()
        for i, (uuid, peer) in enumerate(p.IterPeers()):
            self.assertEqual(uuid, i)
            self.assertEqual(peer.broker.disconnected, 0)
        self.assertEqual(len(p.peers[0]), len(p.peers) - 1)

    def testPickAlive(self):
        p = self._GetPeerForTesting()
        peer = p.PickAlive(0)
        self.assertEqual(peer.broker.disconnected, 0)
        self.assertEqual(len(p.peers[0]), len(p.peers) - 1)

    def testEmptyPickAlive(self):
        p = self._GetPeerForTesting()
        for uuid, peers in p.peers.iteritems():
            for peer in peers:
                peer.broker.disconnected = 1
        for uuid in p.peers:
            self.assertEqual(p.PickAlive(uuid), None)

    def testCheckAlive(self):
        p = pb2pb.Peer()
        mp = MockRemotePeer()
        self.assertEqual(p.CheckAlive(mp), True)
        mp.broker.disconnected = 1
        self.assertEqual(p.CheckAlive(mp), False)
    

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


class TestPing(unittest.TestCase):
    pass


class TestClientCommands(unittest.TestCase):
    pass
