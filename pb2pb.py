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

"""PB2PB is a peer-to-peer overlay network built on Twisted PB.

@author: Damon Kohler
@contact: nessie@googlegroups.com
@license: MIT License
@copyright: 2006 Damon Kohler

"""

__author__ = "Damon Kohler (nessie@googlegroups.com)"

import sys
import random
import uuid
import operator
import time

from twisted.spread import pb
from twisted.internet import defer
from twisted.python import util
from twisted.python import log


class Proxy(pb.Referenceable):

    """Support for third-party references is provided through proxy objects."""

    def __init__(self, proxy_object):
	self.proxy_object = proxy_object

    def callProxy(self, remote_function, *args, **kwargs):
	if self.proxy_object.__class__.__name__ != 'Proxy':
	    return self.proxy_object.callRemote(remote_function,
                                                *args, **kwargs)
	else:
	    return self.proxy_object.callRemote('callProxy', remote_function,
                                                *args, **kwargs)

    def remoteMessageReceived(self, broker, msg, args, kw):
        args = list(broker.unserialize(args))
        kw = broker.unserialize(kw)
        for i, a in enumerate(args):
            if isinstance(a, pb.RemoteReference):
                args[i] = Proxy(a)
        for k, a in kw.iteritems():
            if isinstance(a, pb.RemoteReference):
                kw[k] = Proxy(a)
        state = self.callProxy(msg, *args, **kw)
        return broker.serialize(state, self.perspective)


class PeerProxy(Proxy):

    """Wraps proxy objects for peers to add on-the-fly routing capabilities."""

    def __init__(self, uuid, peer_routes):
        self.peer_routes = peer_routes
        self.uuid = uuid

    def callProxy(self, remote_function, *args, **kwargs):
        # REFACTOR(damonkohler): Create a router object to get the route from.
        # With it like this, I'd have to rewrite the CheckAlive method.
        self.proxy_object = self.peer_routes[0]
        return Proxy.callProxy(self, remote_function, *args, **kwargs)


class Peer(pb.Root):

    """Acts as the communication conduit between any two peers.

    This is the first object exchanged when a connection takes
    place. It is used to facilitate initial communication and store
    connections to other peers.
    
    """

    def __init__(self):
        self.peers = {}
        self.services = []
        self.original_bases = self.__class__.__bases__
        self.uuid = str(uuid.uuid4())
        self.last_update_serial = 0
        self.listeners = []
        self.connectors = []

    def IterPeers(self):
        for uuid in self.peers.keys():
            peer = self.PickAlive(uuid)
            if peer is not None:
                yield uuid, peer
            else:
                del self.peers[uuid]

    def IterDirectPeers(self):
        direct_peers = [(uuid, p[0]) for (uuid, p) in self.peers.iteritems()
                        if p[0].direct]
        for uuid, peer in direct_peers:
            yield uuid, peer

    def PickAlive(self, uuid):
        for i, route in enumerate(self.peers[uuid]):
            if self.CheckAlive(route):
                return route
            else:
                del self.peers[uuid][i]
        return None

    def CheckAlive(self, peer):
        return not peer.broker.disconnected
    
    def AddPeer(self, uuid, peer, direct=False):
        """Add a peer to the dict of peers.

        Each peer is really a prioritized queue of objects
        representing the peer with the specified UUID.

        """
        log.msg("Adding peer %s." % uuid, debug=1)
        peer.direct = direct
        if uuid != self.uuid:
            if peer not in self.peers.setdefault(uuid, []):
                self.peers[uuid].append(peer)

    def UpdateRemotePeers(self, update_serial=0):
        """Updates all remote peers with all currently known peers.

        When called locally, a new update_serial is generated and
        transmited with the requests for remote peers to also send out
        updates. Remote requests to update peers only happen once per
        update_serial until a new update_serial is received.

        """
        log.msg("Updating remote peers.", debug=1)
        if not update_serial:
            update_serial = self.last_update_serial = random.randint(0, 255)
        dl = []
        for uuid, peer in self.IterDirectPeers():
            log.msg("..Operating on direct peer %s" % uuid, debug=1)
            log.msg("....Updating peer.", debug=1)
            d = self._GiveProxyPeers(uuid, peer)
            def push_update(unused_arg):
                log.msg("....Pushing update.", debug=1)
                return peer.callRemote('UpdateRemotePeers', update_serial)
            d.addCallback(push_update)
            dl.append(d)
        return defer.DeferredList(dl)

    def _GiveProxyPeers(self, uuid, peer):
        """Gives ProxyPeer objects of all peers to a remote peer.
        
        @todo: PeerProxies actually contain list of all possible
        routes so that the best can be picked on the fly at a later
        time.  Peers should have only one proxy for any particular
        peer from each peer. That means this function either needs to
        send along its own UUID or possibly perspectives could be
        used.

        """
        proxy_peers = [(u, PeerProxy(u, p)) for u, p in
                       self.peers.iteritems() if u != uuid]
        dl = []
        for uuid, proxy_peer in proxy_peers:
            d = peer.callRemote('AddPeer', uuid, proxy_peer)
            d.addErrback(lambda reason: "Error %s" % reason.value)
            d.addErrback(util.println)
            dl.append(d)
        return defer.DeferredList(dl)
    
    def ExchangePeers(self, peer):
        dl = []
        # TODO(damonkohler): Add errbacks.
        dl.append(peer.callRemote('AddPeer', self.uuid, self, direct=True))
        d = peer.callRemote('GetUUID')
        def add_peer(uuid):
            peer.direct = True
            self.peers[uuid] = [peer]
        d.addCallback(add_peer)
        dl.append(d)
        d = defer.DeferredList(dl)
        return d
        
    def UpdateServices(self, services_to_add=[]):
        """Services can be added through dynamicly loaded mix-ins."""
        if services_to_add:
            self.services.extend(services_to_add)
        self.__class__.__bases__ = self.original_bases + tuple(self.services)

    def remote_AddPeer(self, uuid, peer, direct=False):
        self.AddPeer(uuid, peer, direct=direct)

    def remote_UpdateRemotePeers(self, update_serial):
        """Initiates a remote peer update.
        
        @todo: If I were using Avatars and views I would know who
        called me and I could avoid sending them updates. This is a
        good idea because I obviously won't know anything more than
        they do.

        """
        log.msg("Asked to do update #%d of remote peers." % update_serial,
                debug=1)
        if update_serial != self.last_update_serial:
            self.last_update_serial = update_serial
            return self.UpdateRemotePeers(update_serial)
        log.msg("Already did update #%d. Skipped." % update_serial, debug=1)

    def remote_GetUUID(self):
        log.msg("Sending UUID.", debug=1)
        return self.uuid
    

class Chat():
    chat_file = sys.stdout
    chat_format = '>%s\n'
    
    def Say(self, msg):
        for uuid, p in self.IterPeers():
            d = p.callRemote('Say', msg)
            d.addErrback(lambda reason: "Error %s" % reason.value)
            d.addErrback(util.println)

    def _SayToFile(self, msg):
        self.chat_file.write(self.chat_format % msg)
        
    def remote_Say(self, msg):
        self._SayToFile(msg)


class Ping():

    """Provides methods for pinging peers and measuring latency.

    This is intended to be used as a Peer service.
    
    """
    
    time_module = time
    
    def remote_Ping(self):
        what_time = self.time_module.time()
        log.msg("Peer %s responding to ping with time %s." %
                (self.uuid, what_time), debug=1)
        return what_time

    def _Ping(self, peer):
        start_time = self.time_module.time()
        d = peer.callRemote('Ping')
        d.addCallbacks(lambda end_time: end_time - start_time,
                       lambda reason: "Ping failed: %s" % reason.value)
        d.addErrback(lambda reason: "Ping failed: %s" % reason.value)
        return d

    def PingPeer(self, peer):
        if self.CheckAlive(peer):
            log.msg("Sending ping.", debug=1)
            return self._Ping(peer)
        else:
            log.msg("Unable to ping peer. Peer not alive.", debug=1)
            return None

    def PingUUID(self, uuid):
        """Ping a peer.

        Returns a defered that will return with a ping time or None if
        the host is unreachable.
        
        """
        peer = self.PickAlive(uuid)
        if peer is not None:
            return self._Ping(peer)
        else:
            return None

    def UpdateRouteLatencies(self):
        # TODO(damonkohler): Return a deferred that fires when all the ping
        # deferreds have finished. Can be used to then sort routes by latency.
        for uuid, routes in self.peers.iteritems():
            for route in routes:
                if CheckAlive(route):
                    d = self.PingPeer(route)
                    d.addCallback(lambda latency:
                                  self._UpdateRouteLatency(route, latency))

    def _UpdateRouteLatency(self, route, latency):
        route.latency = latency

    def LatencySortRoutes(self):
        for uuid, routes in self.peers.iteritems():
            routes.sort(key=operator.attrgetter('latency'))

