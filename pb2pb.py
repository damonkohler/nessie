import sys
import optparse
import random
import uuid

import zope.interface

from twisted.spread import pb
from twisted.internet import reactor
from twisted.internet import interfaces
from twisted.python import util
from twisted.python import log


class curry:
    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()

    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs

        return self.fun(*(self.pending + args), **kw)


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
        args = broker.unserialize(args)
        kw = broker.unserialize(kw)
        state = self.callProxy(msg, *args, **kw)
        return broker.serialize(state, self.perspective)

class ConsoleInput(object):
    zope.interface.implements(interfaces.IReadDescriptor)

    def __init__(self, chat):
        self.chat = chat

    def fileno(self):
        return 0

    def connectionLost(self, reason):
        print "Lost connection because %s" % reason

    def doRead(self):
        self.chat.Say(sys.stdin.readline().strip())
       
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
        
    def AddPeer(self, peer, uuid):
        log.msg("Adding peer %s." % uuid, debug=1)
        if uuid not in self.peers and uuid != self.uuid:
            self.peers[uuid] = peer
        

    def UpdateRemotePeers(self):
        """Updates all remote peers with all currently known peers.

        When called locally, a new update_serial is generated and transmited
        with the requests for remote peers to also send out updates. Remote
        requests to update peers only happen once per update_serial until a new
        update_serial is received.

        """
        log.msg("Updating remote peers.", debug=1)
        log.msg(self.peers, debug=1)
        for uuid, peer in self.peers.iteritems():
            log.msg("..Updating remote peer.", debug=1)
            proxy_peers = [(Proxy(p), uuid) for uuid, p in
                           self.peers.iteritems()]
            map(lambda p: peer.callRemote('AddPeer', *p), proxy_peers)

    def ExchangePeers(self, peer):
        # TODO(damonkohler): Add errbacks.
        d = peer.callRemote('AddPeer', self, self.uuid)
        d = peer.callRemote('GetUUID')
        d.addCallback(lambda uuid: self.AddPeer(peer, uuid))
        d.addCallback(lambda _: self.UpdateRemotePeers())
        d.addCallback(lambda _: peer.callRemote('UpdateRemotePeers'))
        
    def UpdateServices(self, services_to_add=[]):
        """Services can be added through dynamicly loaded mix-ins."""
        if services_to_add:
            self.services.extend(services_to_add)
        self.__class__.__bases__ = self.original_bases + tuple(self.services)

    def remote_AddPeer(self, peer, uuid):
        self.AddPeer(peer, uuid)

    def remote_UpdateRemotePeers(self):
        log.msg("Asked to update remote peers.", debug=1)
        self.UpdateRemotePeers()

    def remote_GetUUID(self):
        log.msg("Sending UUID.", debug=1)
        return self.uuid
    

class Chat():
    def Say(self, msg):
        for p in self.peers.itervalues():
            p.callRemote('Say', msg)

    def remote_Say(self, msg):
        print ">%s" % msg


def main():
    parser = optparse.OptionParser()
    parser.add_option('--host', dest='host', help='Host to connect to.')
    options, args = parser.parse_args()

    # TODO(damonkohler): Validate the host string.
    host = options.host
    port = 8790    

    log.startLogging(sys.stdout)

    # Create our root Peer object.
    root_peer = Peer()
    root_peer.UpdateServices(services_to_add=[Chat])

    # Set up reading for STDIN.
    ci = ConsoleInput(root_peer)
    reactor.addReader(ci)

    if host:
        factory = pb.PBClientFactory()
        print "Connecting to %s..." % host
        reactor.connectTCP(host, port, factory)
        d = factory.getRootObject()
        d.addCallback(root_peer.ExchangePeers)
        d.addErrback(lambda reason: "Error %s" % reason.value)
        d.addErrback(util.println)
    else:
        print "Listening..."
        factory = pb.PBServerFactory(root_peer)
        reactor.listenTCP(port, factory)

    reactor.run()

if __name__ == '__main__':
    main()
