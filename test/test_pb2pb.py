## Copyright (c) 2006 Damon Kohler

## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""Tests for pb2pb.

@author: Damon Kohler
@contact: nessie@googlegroups.com
@license: MIT License
@copyright: 2006 Damon Kohler

"""

__author__ = "Damon Kohler (nessie@googlegroups.com)"

from twisted.trial import unittest
from twisted.internet import reactor, defer
from twisted.spread import pb
from twisted.python import util, log

from nessie import pb2pb
from nessie.test import mocks
from nessie.util import curry


WHAT_TIME = 42


class NetworkTestingHelpers(object):

    """A mix-in for TestCases that provides handy network testing functions."""

    def SetUpServer(self, port):
        """Sets up a server to test with.

        @todo: Services are added to the bases for the Peer class. So,
        all future Peer objects will have the changes in them. The
        intent was to modify instances, not the class itself. I'm not
        sure why this ever worked, but it's failing now and needs to
        be rethought.

        """
        root_peer = pb2pb.Peer()
        #root_peer.UpdateServices((pb2pb.Ping,))
        root_peer.Listen(port)
        return root_peer

    def SetUpAliceAndBob(self, alice_port=8790, bob_port=8791):
        """Sets up two connected peers.

        Also, asserts that the connection was successful.
        
        """
        alice = self.SetUpServer(alice_port)
        bob = self.SetUpServer(bob_port)
        dl = (alice.Connect('localhost', bob_port),
              bob.Connect('localhost', alice_port))
        d = defer.DeferredList(dl)
        def assert_connects(unused_arg):
            self.assertEqual(len(alice.peers), 1)
            self.assertEqual(len(bob.peers), 1)
            log.msg("Alice's peers are %s" % alice.peers, debug=1)
            log.msg("Bob's peers are %s" % bob.peers, debug=1)
            self.assert_(bob.uuid in alice.peers)
            self.assert_(alice.uuid in bob.peers)
            self.assert_(alice.peers[bob.uuid][0].direct)
            self.assert_(bob.peers[alice.uuid][0].direct)
        d.addCallback(assert_connects)
        return alice, bob, d

    def SetUpStar(self, num_spokes):
        hub_port = 8790
        spoke_ports = range(8791, 8791 + num_spokes)
        hub_peer = self.SetUpServer(hub_port)
        spoke_peers = [self.SetUpServer(port) for port in spoke_ports]
        dl = []
        for port in spoke_ports:
            dl.append(hub_peer.Connect(port))
        d = defer.DeferredList(dl)
        def assert_connects(unused_arg):
            self.assertEqual(len(hub_peer.peers), num_spokes)
            for p in spoke_peers:
                self.assertEqual(len(p.peers), 1)
                # All spoke peers should be directly connected to the hub.
                self.assert_(p.peers[hub_peer.uuid][0].direct)
                # Hub peer should be directly connected to all spoke peers.
                self.assert_(hub_peer.peers[p.uuid][0].direct)
        d.addCallback(assert_connects)
        return hub_peer, spoke_peers, d

    def SetUpRing(self, num_peers):
        ports = range(8790, 8790 + num_peers)
        peers = [self.SetUpServer(port) for port in ports]
        dl = []
        for i, peer in enumerate(peers):
            if i < num_peers - 1:
                dl.append(peer.Connect(ports[i + 1]))
            else:
                dl.append(peer.Connect(ports[0]))
        return peers, defer.DeferredList(dl)
        
    def CleanUpPeers(self, root_peers):
        log.msg("Cleaning up root peers.", debug=1)
        dl = []
        for rp in root_peers:
            if rp.listener:
                dl.append(rp.listener.stopListening())
                log.msg("Stopped listener on root peer %s." % rp.uuid, debug=1)
        d = defer.DeferredList(dl)
        def do_disconnects(unused_arg):
            for rp in root_peers:
                for connector in rp.connectors:
                    connector.disconnect()
                log.msg("Disconnected %d connections made by root peer %s." %
                        (len(rp.connectors), rp.uuid), debug=1)
        d.addCallback(do_disconnects)
        return d

    def PingTestPeers(self, root_peers):
        log.msg("Doing ping test of root peers.", debug=1)
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


class TestAliceAndBob(unittest.TestCase, NetworkTestingHelpers):

    def tearDown(self):
        self.CleanUpPeers((alice, bob))

    def testSetUpAliceAndBob(self):
        alice, bob, d = self.SetUpAliceAndBob()
        self.assert_(isinstance(alice, pb2pb.Peer))
        self.assert_(isinstance(bob, pb2pb.Peer))
        return d


TestAliceAndBob.skip = 'Failing due to cred transition.'


class TestPeerWithMocks(unittest.TestCase):
    
    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)

    def tearDown(self):
        pass # Nothing to cleanup when doing tests with mocks.

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

    def testUpdateServices(self):
        class MockService(): pass
        p = pb2pb.Peer()
        p.UpdateServices([MockService])
        self.assert_(MockService in p.__class__.__bases__)

    def testUpdateServicesWithNoServices(self):
        p = pb2pb.Peer()
        p.UpdateServices()
        self.assertEqual(p.__class__.__bases__, p.original_bases)


class TestGiveProxyPeers(unittest.TestCase, NetworkTestingHelpers):
    
    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)

    def tearDown(self):
        # REFACTOR(damonkohler): This method of cleanup leaves an unclean
        # reactor on test failures.
        self.CleanUpPeers(self.cleanup)
        
    def test_GiveProxyPeers(self):
        alice_port, bob_port = 8790, 8791
        cindy_port, dave_port = 8792, 8793
        dl = []
        alice, bob, d = self.SetUpAliceAndBob(alice_port=alice_port,
                                               bob_port=bob_port)
        dl.append(d)
        cindy, dave, d = self.SetUpAliceAndBob(alice_port=cindy_port,
                                                bob_port=dave_port)
        self.cleanup = [alice, bob, cindy, dave]
        dl.append(d)
        d = defer.DeferredList(dl)
        d.addCallback(lambda _: cindy.Connect(alice_port))
        d.addCallback(lambda _: dave.Connect(alice_port))
        d.addCallback(
            lambda _: alice._GiveProxyPeers(bob.uuid, alice.peers[bob.uuid][0]))
        def do_asserts(unused_arg):
            self.assertEqual(len(alice.peers), len(bob.peers))
        d.addCallback(do_asserts)
        return d


TestGiveProxyPeers.skip = 'Failing due to cred transition.'


class TestProxyChain(unittest.TestCase, NetworkTestingHelpers):
    
    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)

    def tearDown(self):
        # REFACTOR(damonkohler): This method of cleanup leaves an unclean
        # reactor on test failures.
        self.CleanUpPeers(self.cleanup)
        
    def testProxyChain(self):
        alice_port, bob_port = 8790, 8791
        cindy_port, dave_port = 8792, 8793
        dl = []
        alice, bob, d = self.SetUpAliceAndBob(alice_port=alice_port,
                                               bob_port=bob_port)
        dl.append(d)
        cindy, dave, d = self.SetUpAliceAndBob(alice_port=cindy_port,
                                                bob_port=dave_port)
        self.cleanup = [alice, bob, cindy, dave]
        dl.append(d)
        d = defer.DeferredList(dl)
        d.addCallback(lambda _: bob.Connect(cindy_port))
        d.addCallback(lambda _: bob.UpdateRemotePeers())
        d.addCallback(lambda _: self.PingTestPeers([alice, bob, cindy, dave]))
        return d


TestProxyChain.skip = 'Failing due to cred transition.'


class TestSimpleNetwork(unittest.TestCase, NetworkTestingHelpers):
    
    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)

    def tearDown(self):
        # REFACTOR(damonkohler): This method of cleanup leaves an unclean
        # reactor on test failures.
        return self.CleanUpPeers(self.cleanup)
        
    def testSimpleNetwork(self):
        """Tests a simple network betwen Alice and Bob.

        This also directly tests ExchangePeers through the PeerTesting service
        Conenct method.
        """
        alice, bob, d = self.SetUpAliceAndBob()
        self.cleanup = [alice, bob]
        d.addCallback(lambda _: alice.UpdateRemotePeers())
        d.addCallback(lambda _: self.PingTestPeers([alice, bob]))
        return d


TestSimpleNetwork.skip = 'Failing due to cred transition.'


class TestSimpleNetworkReverseUpdate(unittest.TestCase, NetworkTestingHelpers):
    
    """This used to expose a bug in UpdateRemotePeers.

    The bug was exposed if Bob initiates the update. The same peer
    which initiated the connection to the other peer also had to
    initiate the update or exceptions were raised.

    This bug probably isn't fixed yet, but is averted now because
    _GiveProxyPeers no longer tries to send a PeerProxy of the target
    peer to the target peer itself.

    """    

    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)

    def tearDown(self):
        # REFACTOR(damonkohler): This method of cleanup leaves an unclean
        # reactor on test failures.
        return self.CleanUpPeers(self.cleanup)
        
    def testSimpleNetwork(self):
        """Tests a simple network betwen Alice and Bob.

        This also directly tests ExchangePeers through the PeerTesting
        service Conenct method. Instead of Alice starting the update,
        now Bob does.

        """
        alice, bob, d = self.SetUpAliceAndBob()
        self.cleanup = [alice, bob]
        d.addCallback(lambda _: bob.UpdateRemotePeers())
        d.addCallback(lambda _: self.PingTestPeers([alice, bob]))
        return d


TestSimpleNetworkReverseUpdate.skip = 'Failing due to cred transition.'


class TestStarNetwork(unittest.TestCase, NetworkTestingHelpers):
    
    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)
        
    def tearDown(self):
        # REFACTOR(damonkohler): This method of cleanup leaves an unclean
        # reactor on test failures.
        return self.CleanUpPeers(self.cleanup)

    def testStarNetwork(self):
        num_spokes = 5
        hub_peer, spoke_peers, d = self.SetUpStar(num_spokes)
        self.cleanup = [hub_peer] + spoke_peers
        d.addCallback(lambda _: hub_peer.UpdateRemotePeers())
        def assert_successful_update(unused_arg):
            self.assertEqual(len(hub_peer.peers), num_spokes)
            for p in spoke_peers:
                self.assertEqual(len(p.peers), num_spokes),
            return self.PingTestPeers([hub_peer] + spoke_peers)
        d.addCallback(assert_successful_update)
        return d


TestStarNetwork.skip = 'Failing due to cred transition.'


class TestRingNetwork(unittest.TestCase, NetworkTestingHelpers):
    
    def setUp(self):
        pb2pb.Ping.time_module = mocks.MockTime(WHAT_TIME)
        
    def tearDown(self):
        # REFACTOR(damonkohler): This method of cleanup leaves an unclean
        # reactor on test failures.
        return self.CleanUpPeers(self.cleanup)

    def testRingNetwork(self):
        num_peers = 6
        peers, d = self.SetUpRing(num_peers)
        self.cleanup = peers
        d.addCallback(lambda _: peers[0].UpdateRemotePeers())
        d.addCallback(lambda _: self.PingTestPeers(peers))
        return d


TestRingNetwork.skip = 'Failing due to cred transition.'


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


#TestChat.skip = 'Failing due to cred transition.'


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


TestPing.skip = 'Failing due to cred transition.'
