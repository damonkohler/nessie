import optparse

from twisted.spread import pb, jelly
from twisted.internet import reactor
from twisted.python import util


class Proxy(pb.Referenceable):
    def __init__(self, proxy_object):
	self.proxy_object = proxy_object

    def remote_callProxy(self, remote_function, *args, **kwargs):
	if self.proxy_object.__class__.__name__ != 'Proxy':
	    self.proxy_object.callRemote(remote_function, *args, **kwargs)
	else:
	    self.proxy_object.callRemote('callProxy', remote_function, *args, **kwargs)


class Refer(pb.Root):
    def __init__(self):
	self.ref = None
	self.ref_proxy = None

    def remote_GiveRef(self, ref):
	print "Got remote refer."
	self.ref = ref
	#self.ref.callRemote('Test')

    def remote_Test(self):
	print "Hello World!"

    def remote_GetRef(self):
	print "Giving ref."
	if self.ref is not None:
	    print "Giving proxy."
	    self.ref_proxy = Proxy(self.ref)
	    return self.ref_proxy
	else:
	    return None

    def SetRef(self, ref):
	print "Got root."
	self.ref = ref
	#self.ref.callRemote('Test')
	self.BeginChainingTest()

    def BeginChainingTest(self):
	print "Testing chaining."
	d = self.ref.callRemote('GetRef')
	d.addCallback(self._ChainingTest)
    
    def _ChainingTest(self, ref):
	if ref is None:
	    print "No chain to test. Giving ref."
	    self.ref.callRemote('GiveRef', self)
	else:
	    print "Testing chain."
	    ref.callRemote('callProxy', 'Test')


def main():
    parser = optparse.OptionParser()
    parser.add_option('--host', dest='host', help='Host to connect to.')
    parser.add_option('--port', dest='port', help='Port to listen on.')
    options, args = parser.parse_args()

    r = Refer()

    if options.host:
        # TODO(damonkohler): Validate the host string.
        host = options.host
        factory = pb.PBClientFactory()
        print "Connecting to %s..." % host
	addr, port = host.split(':')
        reactor.connectTCP(addr, int(port), factory)
        d = factory.getRootObject()
        d.addCallback(r.SetRef)
        d.addErrback(lambda reason: "error %s" % reason.value)
        d.addErrback(util.println)
    else:
        print "Listening..."
        factory = pb.PBServerFactory(r)
        reactor.listenTCP(int(options.port), factory)

    reactor.run()


if __name__ == '__main__':
    main()
