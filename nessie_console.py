#!/usr/bin/python -i

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

"""Nessie is P2P darknet."""

__author__ = "damonkohler@gmail.com (Damon Kohler)"

import sys
import socket
import nessie

WELCOME = """Welcome to Nessie.

You are node http://%s:%s.
Add peers with: me.AddPeer(peer_id)
Send chat messages to peers with: me.Chat('Hello Peer!')"""


class NessieConsole(nessie.Nessie):

  """A P2P darknet."""

  def Chat(self, msg):
    """Send a message to every peer that will appear in their console."""
    msg = self._Encrypt(msg)
    self.Broadcast('PrintMessage', msg)

  def export_PrintMessage(self, peer_id, msg):
    """Print a message."""
    msg = self._Decrypt(msg)
    print '%s> %s' % (peer_id, msg)
    # NOTE(damonkohler): Could also enable marshalling None, but that may not
    # be cross language compatible?
    return 0


if __name__ == '__main__':
  if len(sys.argv) != 5:
    print 'nessie.py host port peer_id network_id'
    sys.exit(1)
  host, port = socket.gethostbyname(sys.argv[1]), int(sys.argv[2])
  peer_id, network_id = sys.argv[3:5]
  me = NessieConsole(peer_id, network_id, host, port)
  me.Serve()
  print WELCOME % (host, port)
