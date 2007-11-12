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
import node
import opendht
import hashlib
import random
import struct
from Crypto.Cipher import AES

WELCOME = """Welcome to Nessie.

You are node http://%s:%s.
Add peers with: me.AddPeer(user_id)
Send chat messages to peers with: me.Chat('Hello Peer!')"""


def Pad(value, block_size):
  """Pad value to block_size using ISO 10126 standard."""
  assert block_size < 256
  pad_length = block_size - (len(value) % block_size)
  if not pad_length:
    # Always pad at least 1 block.
    pad_length = block_size
  padding = [random.randint(0, 255) for _ in range(pad_length)]
  padding[-1] = len(padding)
  padding = struct.pack('B' * len(padding), *padding)
  return value + padding


def RemovePadding(value):
  """The last byte is the length of the padding."""
  pad_length = struct.unpack('B', value[-1])[0]
  return value[:-pad_length]


def Encrypt(key, value):
  """Encrypt with AES and a 32-byte key."""
  key = key.zfill(32)[:32]
  value = Pad(value, 16)
  aes = AES.new(key, AES.MODE_ECB)
  return aes.encrypt(value)


def Decrypt(key, value):
  """Decrypt with AES and a 32-byte key."""
  key = key.zfill(32)[:32]
  aes = AES.new(key, AES.MODE_ECB)
  value = aes.decrypt(value)
  return RemovePadding(value)


class DumbDht(object):

  """A simulated DHT for manual testing."""

  def __init__(self):
    self._dht = {}

  def Put(self, key, value):
    self._dht[key] = value

  def Get(self, key):
    return self._dht[key]

  def Remove(self, key, value, secret):
    assert key in self._dht
    assert value == self._dht[key]
    del self._dht[key]


class Nessie(object):

  """A P2P darknet."""

  def __init__(self, user_id, network_id):
    self.user_id = user_id
    self.network_id = network_id
    self._node = None
    self._dht = DumbDht()

  def _GetServerKey(self, user_id):
    """Server keys are a hash of your user ID and the network ID."""
    return hashlib.sha224(user_id + self.network_id).hexdigest()

  def _Announce(self, host, port):
    """Announce your server by publishing its address to the DHT."""
    key = self._GetServerKey(self.user_id)
    value = Encrypt(self.network_id, '%s:%d' % (host, port))
    self._dht.Put(key, value)

  def AddPeer(self, user_id):
    """Add a peer that has announced their server."""
    key = self._GetServerKey(user_id)
    value = self._dht.Get(key)
    value = Decrypt(self.network_id, value)
    host, port = value.split(':')
    port = int(port)
    self._node.AddPeer(host, port)

  def Serve(self, host, port):
    """Start a server on host:port and announce it."""
    self._node = node.Node(host, port)
    self._node.Serve()
    self._Announce(host, port)

  def Chat(self, msg):
    """Send a message to every peer that will appear in their console."""
    self._node.Broadcast('PrintMessage', msg)


if __name__ == '__main__':
  address = sys.argv[1], int(sys.argv[2])
  id = sys.argv[3:5]
  me = Nessie(*id)
  me.Serve(*address)
  print WELCOME % address
