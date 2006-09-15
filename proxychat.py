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
	    self.proxy_object.callRemote('callProxy', remote_function, *args, **kwargs)


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


class Chat(pb.Root):
    def __init__(self):
        self.chats = []
	self.proxy_chats = []
        
    def remote_Say(self, message):
        print '>%s' % message
        
    def remote_GiveChat(self, chat):
        print "New user joined chat."
        self.chats.append(chat)
	print "Sharing chats via proxy."
	for c in self.chats:
	    if c is not chat:
		chat.callRemote('GiveProxyChat', Proxy(c))
		c.callRemote('GiveProxyChat', Proxy(chat))

    def remote_GiveProxyChat(self, proxy_chat):
	print "New proxy user joined chat."
	self.proxy_chats.append(proxy_chat)

    def JoinChat(self, chat):
        print "Joined new chat."
        chat.callRemote('GiveChat', self)
        self.chats.append(chat)

    def Say(self, message):
        for c in self.chats:
            c.callRemote('Say', message)
	for pc in self.proxy_chats:
	    pc.callRemote('callProxy', 'Say', message)


def main():
    parser = optparse.OptionParser()
    parser.add_option('--host', dest='host', help='Host to connect to.')
    options, args = parser.parse_args()

    chat = Chat()
    ci = ConsoleInput(chat)
    reactor.addReader(ci)

    if options.host:
        # TODO(damonkohler): Validate the host string.
        host = options.host
        factory = pb.PBClientFactory()
        print "Connecting to %s..." % host
        reactor.connectTCP(host, 8790, factory)
        d = factory.getRootObject()
        d.addCallback(chat.JoinChat)
        d.addErrback(lambda reason: "error %s" % reason.value)
        d.addErrback(util.println)
    else:
        print "Listening..."
        factory = pb.PBServerFactory(chat)
        reactor.listenTCP(8790, factory)

    reactor.run()

if __name__ == '__main__':
    main()
