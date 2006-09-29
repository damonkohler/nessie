from twisted.trial import unittest

import pb2pb
import mocks


class TestPeer(unittest.TestCase):
    def _GetPeerForTesting(self):
        p = pb2pb.Peer()
        p.peers = {0: [], 1: [], 2: []}
        for uuid, routes in p.peers.iteritems():
            for i in range(len(p.peers)):
                p.peers[uuid].append(mocks.MockRemotePeer())
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
        mp = mocks.MockRemotePeer()
        self.assertEqual(p.CheckAlive(mp), True)
        mp.broker.disconnected = 1
        self.assertEqual(p.CheckAlive(mp), False)

    def testAddFirstPeer(self):
        pass

    def testAddAdditionalPeers(self):
        pass

    def test_remote_GetUUID(self):
        p = pb2pb.Peer()
        self.assertEqual(p.remote_GetUUID(), p.uuid)

    def testUpdateServices(self):
        pass


class TestProxy(unittest.TestCase):
    pass


class TestPeerProxy(unittest.TestCase):
    pass


class TestChat(unittest.TestCase):
    def test_remote_Say(self):
        msg = 'Hello World!'
        mf = mocks.MockFile()
        chat = pb2pb.Chat()
        chat.chat_file = mf
        chat.remote_Say(msg)
        self.assertEqual([chat.chat_format % msg], mf.write_lines)
        
    def test_SayToFile(self):
        msg = 'Hello World!'
        mf = mocks.MockFile()
        chat = pb2pb.Chat()
        chat.chat_file = mf
        chat._SayToFile(msg)
        self.assertEqual([chat.chat_format % msg], mf.write_lines)


class TestPing(unittest.TestCase):
    pass

