#!/usr/bin/python

# The MIT License
#
# Copyright (c) 2007 Damon Kohler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""A node in a Nessie darknet."""

__author__ = "damonkohler@gmail.com (Damon Kohler)"

import SimpleXMLRPCServer
import socket
import threading
import xmlrpclib


class Node(object):

  """Nodes have collections of peers to communicate with."""

  def __init__(self, host, port):
    self.server = SimpleXMLRPCServer.SimpleXMLRPCServer((host, port))
    self.server.register_function(self.PrintMessage)
    self.peers = {}

  def PrintMessage(self, msg):
    """Print a message."""
    print msg
    # NOTE(damonkohler): Could also enable marshalling None, but that may not
    # be cross language compatible?
    return 0

  def Broadcast(self, method, *args, **kwargs):
    """Call the same method on all peers."""
    for peer in self.peers.values():
      m = getattr(peer, method)
      m(*args, **kwargs)

  def AddPeer(self, host, port):
    """Add a peer and to the dict of peers."""
    peer = self.Connect(host, port)
    self.peers[(host, port)] = peer
    return peer

  def Connect(self, host, port):
    """Return a ServerProxy to host:port."""
    return xmlrpclib.ServerProxy('http://%s:%s' % (host, port))

  def Serve(self):
    """Start serving indefinitely."""
    def ServerThread():
      self.server.serve_forever()
    t = threading.Thread(target=ServerThread)
    t.setDaemon(True)
    t.start()
