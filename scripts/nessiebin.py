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

"""Nessie binary.

This is the entry point for Nessie. The intent is for this to be
easily extensible with out more specific front-ends/clients. For
example, console and AJAX clients. Clients should be part of the
clients pacakage.

@author: Damon Kohler
@contact: nessie@googlegroups.com
@license: MIT License
@copyright: 2006 Damon Kohler

"""

__author__ = "Damon Kohler (nessie@googlegroups.com)"

import sys
import optparse
import uuid

import zope.interface

from twisted.internet import reactor
from twisted.cred import portal, checkers
from twisted.spread import pb
from twisted.python import util, log

from nessie import pb2pb
from nessie import client
from nessie import credible


class BasicClientCommands():
    
    def client_connect(self, host, port):
        d = self.Authenticate(host, port)

        d.addCallback(self.ExchangePeers)
        d.addCallback(lambda _: self.UpdateRemotePeers())
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
    root_peer = pb2pb.Peer()
    root_peer.UpdateServices(services_to_add=[pb2pb.Chat, pb2pb.Ping,
                                              BasicClientCommands])

    # Set up reading for STDIN.
    ci = client.console.ConsoleInput(root_peer)
    reactor.addReader(ci)

    root_peer.StartListening(port=listen_port)

    reactor.run()


if __name__ == '__main__':
    main()
