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
        self.last_update_serial = 0
        
    def AddPeer(self, peer, uuid):
        log.msg("Adding peer %s." % uuid, debug=1)
        if uuid not in self.peers and uuid != self.uuid:
            self.peers[uuid] = peer
        
    def UpdateRemotePeers(self, update_serial=0):
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
    def Say(self, msg):
        for p in self.peers.itervalues():
            p.callRemote('Say', msg)

    def remote_Say(self, msg):
        print ">%s" % msg


def main():
    parser = optparse.OptionParser()
    parser.add_option('--port', dest='port', default=8790,
                      help='Port to listen on.')
    parser.add_option('--host', dest='host', default=':',
                      help='Host to connect to defined as host:port.')
    options, args = parser.parse_args()

    # TODO(damonkohler): Validate the host string.
    host, connect_port = options.host.split(':')
    connect_port = int(connect_port)
    listen_port = int(options.port)

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
        reactor.connectTCP(host, connect_port, factory)
        d = factory.getRootObject()
        d.addCallback(root_peer.ExchangePeers)
        d.addErrback(lambda reason: "Error %s" % reason.value)
        d.addErrback(util.println)
    print "Listening on %d..." % listen_port
    factory = pb.PBServerFactory(root_peer)
    reactor.listenTCP(listen_port, factory)

    reactor.run()

if __name__ == '__main__':
    main()
