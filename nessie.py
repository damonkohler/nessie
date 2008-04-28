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

import base64
from Crypto.Cipher import AES
import hashlib
import logging
import opendht
import random
import SimpleXMLRPCServer
import socket
import struct
import threading
import xmlrpclib

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')


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
  encrypted = aes.encrypt(value)
  return base64.b64encode(encrypted)


def Decrypt(key, value):
  """Decrypt with AES and a 32-byte key."""
  key = key.zfill(32)[:32]
  aes = AES.new(key, AES.MODE_ECB)
  encrypted = base64.b64decode(value)
  decrypted = aes.decrypt(encrypted)
  return RemovePadding(decrypted)


# TODO(damonkohler): This fails for NATed IPs. We need to scrape some external
# server to find our true public IP.
def GetPublicIpAddress():
  # TODO(damonkohler): It might be better to use the address of the peer we're
  # trying to connect to for finding the IP since it may be use another
  # interface.
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  s.connect(('google.com', 80))
  return s.getsockname()[0]


class NessieError(Exception):
  pass


class Nessie(SimpleXMLRPCServer.SimpleXMLRPCServer):

  """Nodes have collections of peers to communicate with."""

  def __init__(self, peer_id, network_id, host, port):
    self.host = host
    self.port = port
    # NOTE(damonkohler): Can't use super because SimpleXMLRPCServer is old
    # style.
    SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, (host, port))
    # A mapping of peer_id and (host, port) to (peer_id, host, port, peer)
    self.peers = {}
    self.peer_id = peer_id
    self.network_id = network_id
    self._dht = opendht.OpenDht(opendht.FindGateway())

  def _dispatch(self, method, args):
    # We are forcing the 'export_' prefix on methods that are callable
    # through XML-RPC to prevent potential security problems.
    return getattr(self, 'export_' + method)(*args)

  def _Encrypt(self, value):
    return Encrypt(self.network_id, value)

  def _Decrypt(self, value):
    return Decrypt(self.network_id, value)

  def _GetServerKey(self, peer_id):
    """Server keys are a hash of your user ID and the network ID."""
    return hashlib.sha224(peer_id + self.network_id).hexdigest()

  def _Announce(self):
    """Announce your server by publishing its address to the DHT."""
    key = self._GetServerKey(self.peer_id)
    logging.debug('Encrypting announcement.')
    value = self._Encrypt('%s:%d' % (self.host, self.port))
    logging.debug('Posting announcement.')
    self._dht.Put(key, value)

  def Broadcast(self, method, *args, **kwargs):
    """Call the same method on all peers."""
    for peer_id, (host, port, peer) in self.peers.iteritems():
      logging.debug('Calling method %r on peer %r.' % (method, peer_id))
      m = getattr(peer, method)
      m(self.peer_id, *args, **kwargs)

  def _LookupPeer(self, peer_id):
    """Return host, port for a published peer_id."""
    key = self._GetServerKey(peer_id)
    values, placemark = self._dht.Get(key)
    if not values:
      raise NessieError('No peers returned for user id %r.' % peer_id)
    # NOTE(damonkohler): Need to accomodate for the possibility of multipe
    # values.
    value = self._Decrypt(values[0])
    host, port = value.split(':')
    port = int(port)
    return host, port

  def AddPeer(self, peer_id):
    """Add a peer that has announced their server."""
    host, port = self._LookupPeer(peer_id)
    logging.debug('Adding peer %r %s:%d.' % (peer_id, host, port))
    peer = xmlrpclib.ServerProxy('http://%s:%s' % (host, port))
    self.peers[peer_id] = host, port, peer

  def GetPeerNicknames(self):
    # HACK(damonkohler): Need to do this because we have multiple keys mapping
    # to each peer. Also, we want to dump the list into a wxListBox and I'm
    # not sure if it will accept any iterator.
    return self.peers.keys()

  def Serve(self):
    """Start serving indefinitely in a separate thread."""
    t = threading.Thread(target=self.serve_forever)
    t.setDaemon(True)
    t.start()
    self._Announce()
