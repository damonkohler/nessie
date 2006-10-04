from twisted.trial import unittest
from twisted.internet import reactor, defer
from twisted.spread import pb
from twisted.python import util
from twisted.python import log

import pb2pb
import mocks
from curry import curry


WHAT_TIME = 42


class PeerTesting():
    """Testing service for peers."""
    def Connect(self, port):
        factory = pb.PBClientFactory()
        self.factory = factory
        self.connector = reactor.connectTCP('localhost', port, factory)
        d = factory.getRootObject()
        d.addCallback(self.ExchangePeers)
        return d


class TestPeer(unittest.TestCase):
    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)

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

    def test_remote_GetUUID(self):
        p = pb2pb.Peer()
        self.assertEqual(p.remote_GetUUID(), p.uuid)

    def testUpdateServices(self):
        self.fail()

    testUpdateServices.todo = 'todo'

    def _SetUpServer(self, port):
        root_peer = pb2pb.Peer()
        root_peer.UpdateServices([PeerTesting, pb2pb.Ping])
        factory = pb.PBServerFactory(root_peer)
        root_peer.listener = reactor.listenTCP(port, factory)
        return root_peer

    def test_GiveProxyPeers(self):
        alice_port, bob_port = 8790, 8791
        cindy_port, dave_port = 8792, 8793
        dl = []
        alice, bob, d = self._SetUpAliceAndBob(alice_port=alice_port,
                                               bob_port=bob_port)
        dl.append(d)
        cindy, dave, d = self._SetUpAliceAndBob(alice_port=cindy_port,
                                                bob_port=dave_port)
        dl.append(d)
        d = defer.DeferredList(dl)
        d.addCallback(lambda _: cindy.Connect(alice_port))
        d.addCallback(lambda _: dave.Connect(alice_port))        
        d.addCallback(lambda _: alice._GiveProxyPeers(alice.peers[bob.uuid][0]))
        def do_asserts(unused_arg):
            self.assertEqual(len(alice.peers), len(bob.peers))
        d.addCallback(do_asserts)
        d.addCallback(lambda _: self.CleanUpPeers([alice, bob, cindy, dave]))
        return d

    def _SetUpAliceAndBob(self, alice_port=8790, bob_port=8791):
        """Sets up two connected peers.

        Also, asserts that the connection was successful.
        """
        alice = self._SetUpServer(alice_port)
        bob = self._SetUpServer(bob_port)
        d = alice.Connect(bob_port)
        def assert_connects(unused_arg):
            self.assertEqual(len(alice.peers), 1)
            self.assertEqual(len(bob.peers), 1)
            log.msg("Alice's peers are %s" % alice.peers, debug=1)
            log.msg("Bob's peers are %s" % bob.peers, debug=1)
            self.assert_(bob.uuid in alice.peers)
            self.assert_(alice.uuid in bob.peers)
        d.addCallback(assert_connects)
        return alice, bob, d

    def testSimpleNetwork(self):
        """Tests a simple network betwen Alice and Bob.

        This also directly tests ExchangePeers through the PeerTesting service
        Conenct method.
        """
        alice, bob, d = self._SetUpAliceAndBob()
        d.addCallback(lambda _: alice.UpdateRemotePeers())
        d.addCallback(lambda _: self.PingTestPeers([alice, bob]))
        d.addCallback(lambda _: self.CleanUpPeers([alice, bob]))
        return d
            
    def _ConnectStarNetwork(self, hub_port, spoke_peers):
        dl = []
        for peer in spoke_peers:
            dl.append(peer.Connect(hub_port))
        return defer.DeferredList(dl)

    def testStarNetwork(self):
        hub_port = 8790
        peer_ports = range(8791, 8794)
        hub_peer = self._SetUpServer(hub_port)
        spoke_peers = [self._SetUpServer(port) for port in peer_ports]
        d = self._ConnectStarNetwork(hub_port, spoke_peers)
        def assert_connects(unused_arg):
            self.assertEqual(len(hub_peer.peers), len(peer_ports))
            for p in spoke_peers:
                self.assertEqual(len(p.peers), len(peer_ports),
                                 'Peer %s only has connections to peers %s.' %
                                 (p.uuid, p.peers.keys()))
        d.addCallback(assert_connects)
        d.addCallback(lambda _: self.PingTestPeers([hub_peer] + spoke_peers))
        d.addCallback(lambda _: self.CleanUpPeers([hub_peer] + spoke_peers))
        return d

    # TODO(damonkohler): Re-enable this after fixing peer updates to not
    # generate so many useless routes. Should make it easier to debug.
    testStarNetwork.skip = 1

    def PingTestPeers(self, root_peers):
        dl = []
        for rp in root_peers:
            for uuid, routes in rp.peers.iteritems():
                for r in routes:
                    log.msg('Pinging peer %s from peer %s' % (uuid, rp.uuid),
                            debug=1)
                    d = rp.PingPeer(r)
                    d.addCallback(curry(self.assertEqual, 0))
                    dl.append(d)
        return defer.DeferredList(dl)

    def CleanUpPeers(self, root_peers):
        dl = []
        for rp in root_peers:
            dl.append(rp.listener.stopListening())
            for peers in rp.peers.itervalues():
                for p in peers:
                    p.broker.transport.loseConnection()
        return defer.DeferredList(dl)


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
    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)
        self.ping = pb2pb.Peer()
        self.ping.UpdateServices([pb2pb.Ping])

    def test_remote_Ping(self):
        self.assertEqual(self.ping.remote_Ping(), WHAT_TIME)

    def testPingPeer(self):
        peer = mocks.MockRemotePeer()
        peer.deferred.callback(WHAT_TIME + 1)
        d = self.ping.PingPeer(peer)
        d.addCallback(curry(self.assertEqual, 1))

    def testPingUUID(self):
       self.fail()

    testPingUUID.todo = 'todo'
