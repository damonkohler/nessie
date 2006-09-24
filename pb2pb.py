import sys
import optparse

import zope.interface

from twisted.spread import pb
from twisted.internet import reactor
from twisted.internet import interfaces
from twisted.python import util
from twisted.python import log


class Proxy(pb.Referenceable):
    def __init__(self, proxy_object):
	self.proxy_object = proxy_object

    def remote_callProxy(self, remote_function, *args, **kwargs):
	if self.proxy_object.__class__.__name__ != 'Proxy':
	    self.proxy_object.callRemote(remote_function, *args, **kwargs)
	else:
	    self.proxy_object.callRemote('callProxy', remote_function,
                                         *args, **kwargs)


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
        self.peers = []
	self.proxy_peers = []
        self.services = []
        self.original_bases = self.__class__.__bases__
        
    def AddPeer(self, peer):
        log.msg("Adding peer.", debug=1)
        if peer not in self.peers:
            self.peers.append(peer)

    def UpdateRemotePeers(self):
        log.msg("Updating remote peers.", debug=1)
        all_peers = self.peers + self.proxy_peers
        for peer in all_peers:
            proxy_peers = [Proxy(p) for p in all_peers if p is not peer]
            map(lambda p: peer.callRemote('AddProxyPeer', p), proxy_peers)
            #peer.callRemote('UpdateRemotePeers')

    def ExchangePeers(self, peer):
        # TODO(damonkohler): Add errbacks.
        d = peer.callRemote('AddPeer', self)
        d = peer.callRemote('UpdateRemotePeers')
        self.AddPeer(peer)
        self.UpdateRemotePeers()

    def UpdateServices(self, services_to_add=[]):
        if services_to_add:
            self.services.extend(services_to_add)
        self.__class__.__bases__ = self.original_bases + tuple(self.services)

    def remote_AddPeer(self, peer):
        self.AddPeer(peer)

    def remote_AddProxyPeer(self, proxy_peer):
        log.msg("Adding proxy peer.", debug=1)
	self.proxy_peers.append(proxy_peer)

    def remote_UpdateRemotePeers(self, remote_peers=[]):
        self.UpdateRemotePeers()


class Chat():
    def Say(self, msg):
        for p in self.peers:
            p.callRemote('Say', msg)
        for p in self.proxy_peers:
            p.callRemote('callProxy', 'Say', msg)
        
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
