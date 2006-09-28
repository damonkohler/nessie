import sys
import optparse
import random
import uuid
import operator

import zope.interface

from twisted.spread import pb
from twisted.internet import reactor
from twisted.internet import interfaces
from twisted.python import util
from twisted.python import log


class Proxy(pb.Referenceable):
    def __init__(self, proxy_object):
	self.proxy_object = proxy_object

    def callProxy(self, remote_function, *args, **kwargs):
	if self.proxy_object.__class__.__name__ != 'Proxy':
	    self.proxy_object.callRemote(remote_function, *args, **kwargs)
	else:
	    self.proxy_object.callRemote('callProxy', remote_function,
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
    def __init__(self, uuid, peer_routes):
        self.peer_routes = peer_routes
        self.uuid = uuid

    def callProxy(self, remote_function, *args, **kwargs):
        # REFACTOR(damonkohler): Create a router object to get the route from.
        # With it like this, I'd have to rewrite the CheckAlive method.
        self.proxy_object = self.peer_routes[0]
        Proxy.callProxy(self, remote_function, *args, **kwargs)

class ConsoleInput(object):
    zope.interface.implements(interfaces.IReadDescriptor)

    def __init__(self, peer):
        self.peer = peer

    def fileno(self):
        return 0

    def connectionLost(self, reason):
        print "Lost connection because %s" % reason

    def doRead(self):
        line = sys.stdin.readline().strip()
        if line[0] == '/':
            self.ParseCommand(line)
        else:
            self.peer.Say(line)

    def ParseCommand(self, line):
        tokens = line.split(' ')
        command = tokens[0][1:]
        args = tokens[1:]

        method = getattr(self.peer, "client_%s" % command, None)
        if method is None:
            log.msg("No such command: /%s" % command)
        else:
            try:
                state = method(*args)
            except TypeError:
                log.msg("/%s didn't accept arguments %s" % (command, args))
        
    # TODO(damonkohler): Find out why this is necessary.
    def logPrefix(self):
        return 'ConsoleInput'


class Peer(pb.Root):
    """Acts as the communication conduit between any two peers.

    This is the first object exchanged when a connection takes place. It is
    used to facilitate initial communication and store connections to other
    peers.
    """
    def __init__(self):
        self.peers = {}
        self.services = []
        self.original_bases = self.__class__.__bases__
        self.uuid = str(uuid.uuid4())
        self.last_update_serial = 0

    def IterPeers(self):
        for uuid in self.peers.keys():
            peer = self.PickAlive(uuid)
            if peer is not None:
                yield uuid, peer
            else:
                del self.peers[uuid]

    def PickAlive(self, uuid):
        for i, route in enumerate(self.peers[uuid]):
            if self.CheckAlive(route):
                return route
            else:
                del self.peers[uuid][i]
        return None

    def CheckAlive(self, peer):
        return not peer.broker.disconnected
    
    def AddPeer(self, peer, uuid):
        """Add a peer to the dict of peers.

        Each peer is really a prioritized queue of objects representing the
        peer with the specified UUID.

        TODO(damonkohler): This function might need to be renamed since it
        doesn't clearly indicate that we're actually adding one particular
        route to a peer and not really just the peer itself.
        
        """
        log.msg("Adding peer %s." % uuid, debug=1)
        if uuid != self.uuid:
            if peer not in self.peers.setdefault(uuid, []):
                self.peers[uuid].append(peer)
    
    def UpdateRemotePeers(self, update_serial=0):
        """Updates all remote peers with all currently known peers.

        When called locally, a new update_serial is generated and transmited
        with the requests for remote peers to also send out updates. Remote
        requests to update peers only happen once per update_serial until a new
        update_serial is received.

        """
        log.msg("Updating remote peers.", debug=1)
        log.msg(self.peers, debug=1)
        for uuid, peer in self.IterPeers():
            log.msg("..Updating remote peer.", debug=1)
            proxy_peers = [(PeerProxy(uuid, p), uuid) for uuid, p in
                           self.peers.iteritems()]
            def add_peer(uuid, proxy_peer):
                d = peer.callRemote('AddPeer', uuid, proxy_peer)
                d.addErrback(lambda reason: "Error %s" % reason.value)
                d.addErrback(util.println)
            map(lambda p: add_peer(*p), proxy_peers)
            if not update_serial:
                update_serial = self.last_update_serial = random.randint(0, 255)
            peer.callRemote('UpdateRemotePeers', update_serial)

    def ExchangePeers(self, peer):
        # TODO(damonkohler): Add errbacks.
        d = peer.callRemote('AddPeer', self, self.uuid)
        d = peer.callRemote('GetUUID')
        d.addCallback(lambda uuid: self.AddPeer(peer, uuid))
        d.addCallback(lambda _: self.UpdateRemotePeers())
        
    def UpdateServices(self, services_to_add=[]):
        """Services can be added through dynamicly loaded mix-ins."""
        if services_to_add:
            self.services.extend(services_to_add)
        self.__class__.__bases__ = self.original_bases + tuple(self.services)

    def remote_AddPeer(self, peer, uuid):
        self.AddPeer(peer, uuid)

    def remote_UpdateRemotePeers(self, update_serial):
        log.msg("Asked to update remote peers.", debug=1)
        if update_serial != self.last_update_serial:
            self.last_update_serial = update_serial
            self.UpdateRemotePeers(update_serial)

    def remote_GetUUID(self):
        log.msg("Sending UUID.", debug=1)
        return self.uuid
    

class Chat():
    chat_file = sys.stdout
    chat_format = '>%s'
    
    def Say(self, msg):
        for uuid, p in self.IterPeers():
            d = p.callRemote('Say', msg)
            d.addErrback(lambda reason: "Error %s" % reason.value)
            d.addErrback(util.println)

    def _SayToFile(self, msg, file):
        file.write(self.chat_format % msg)
        
    def remote_Say(self, msg):
        self._SayToFile(msg, self.chat_file)


class Ping():
    def remote_Ping(self):
        return time.time()

    def _Ping(self, peer):
        start_time = time.time()
        d = peer.callRemote('ping')
        d.addCallback(lambda end_time: end_time - start_time)
        d.addErrback(lambda reason: "Ping failed: %s" % reason.value)
        return d

    def PingPeer(self, peer):
        if self.CheckAlive(peer):
            return self._Ping(peer)
        else:
            return None

    def PingUUID(self, uuid):
        """Ping a peer.

        Returns a defered that will return with a ping time or None if the
        host is unreachable.
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
            routes.sort(key=operator.__attrgetter__('latency'))
        
class ClientCommands():
    def client_connect(self, host, port):
        # TODO(damonkohler): Proper parameter validation.
        port = int(port)

        factory = pb.PBClientFactory()
        log.msg("Connecting to %s:%s..." % (host, port))
        reactor.connectTCP(host, port, factory)

        d = factory.getRootObject()
        d.addCallback(self.ExchangePeers)
        d.addErrback(lambda reason: "Error %s" % reason.value)
        d.addErrback(util.println)
        

def main():
    parser = optparse.OptionParser()
    parser.add_option('--port', dest='port', default=8790,
                      help='Port to listen on.')
    options, args = parser.parse_args()

    listen_port = int(options.port)

    log.startLogging(sys.stdout)

    # Create our root Peer object.
    root_peer = Peer()
    root_peer.UpdateServices(services_to_add=[Chat, ClientCommands, Ping])

    # Set up reading for STDIN.
    ci = ConsoleInput(root_peer)
    reactor.addReader(ci)

    log.msg("Listening on %d..." % listen_port)
    factory = pb.PBServerFactory(root_peer)
    reactor.listenTCP(listen_port, factory)

    reactor.run()

if __name__ == '__main__':
    main()
