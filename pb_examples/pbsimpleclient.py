import sys
import zope.interface
from twisted.spread import pb
from twisted.internet import reactor
from twisted.internet import interfaces
from twisted.python import util

factory = pb.PBClientFactory()
reactor.connectTCP("localhost", 8789, factory)

class ConsoleInput(object):
    zope.interface.implements(interfaces.IReadDescriptor)
    
    def fileno(self):
        return 0

    def connectionLost(self, reason):
        print "Lost connection because %s" % reason

    def doRead(self):
        d = self.root.callRemote("echo", sys.stdin.readline().strip())
        d.addCallback(lambda echo: 'Server responds: %s' % echo)
        d.addCallback(util.println)
        d.addErrback(util.println)

    def setRoot(self, root):
        self.root = root

    def logPrefix(self):
        return 'ConsoleInput'

ci = ConsoleInput()
reactor.addReader(ci)

d = factory.getRootObject()
d.addCallback(ci.setRoot)

reactor.run()
