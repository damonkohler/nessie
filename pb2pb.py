import sys
import optparse

import zope.interface

from twisted.spread import pb
from twisted.internet import reactor
from twisted.internet import interfaces
from twisted.python import util


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
        
    def AddPeer(self, peer):
        self.peers.append(peer)

    def UpdateRemotePeers(self, remote_peers=[]):
        if not remote_peers:
            remote_peers = self.peers
        my_peers = self.peers[:]
        my_peers.extend(self.proxy_peers)
        proxies = [Proxy(p) for p in my_peers]
        for rp in remote_peers:
            for p in proxies:
                rp.callRemote('AddProxyPeer', p)

    def ExchangePeers(self, peer):
        self.UpdateRemotePeers(remote_peers=[peer])
        self.AddPeer(peer)
        d = peer.callRemote('AddPeer', self)
        d = peer.callRemote('UpdateRemotePeers', remote_peers=[self])
        # TODO(damonkohler): Add errbacks.
        
    def remote_AddPeer(self, peer):
        self.AddPeer(peer)

    def remote_AddProxyPeer(self, proxy_peer):
	self.proxy_peers.append(proxy_peer)

    def remote_UpdateRemotePeers(self, remote_peers=[]):
        self.UpdateRemotePeers(remote_peers=remote_peers)


def main():
    parser = optparse.OptionParser()
    parser.add_option('--host', dest='host', help='Host to connect to.')
    options, args = parser.parse_args()

    # TODO(damonkohler): Validate the host string.
    host = options.host
    port = 8790    

    # Create our root Peer object.
    root_peer = Peer()

    # Set up reading for STDIN.
    ci = ConsoleInput(chat)
    reactor.addReader(ci)

    if host:
        factory = pb.PBClientFactory()
        print "Connecting to %s..." % host
        reactor.connectTCP(host, port, factory)
        d = factory.getRootObject()
        d.addCallback(root_peer.AddPeer)
        d.addCallback(root_peer.SendRootObject)
        d.addErrback(lambda reason: "Error %s" % reason.value)
        d.addErrback(util.println)
    else:
        print "Listening..."
        factory = pb.PBServerFactory(root_peer)
        reactor.listenTCP(port, factory)

    reactor.run()

if __name__ == '__main__':
    main()
