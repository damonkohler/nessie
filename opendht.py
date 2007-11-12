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

"""An interface to OpenDHT http://opendht.org/."""

__author__ = "damonkohler@gmail.com (Damon Kohler)"

import sha
import xmlrpclib

# Other gateways listed at http://opendht.org/servers.txt. This gateway uses
# OASIS (http://oasis.coralcdn.org/) to find the nearest node.
GATEWAY = 'http://opendht.nyuld.net:5851/'
# Application ID.
APP_ID = 'Nessie'
# Response code to human-readable code mapping.
RESPONSES = {0: 'Success', 1: 'Capacity', 2: 'Again'}
# Time to live for puts and removes.
TTL = 3600


class OpenDht(object):

  def __init__(self, gateway=GATEWAY):
    self.server = xmlrpclib.ServerProxy(gateway)

  def _EncodeHash(self, value):
    return xmlrpclib.Binary(sha.new(value).digest())

  def Put(self, key, value, ttl=TTL, secret=''):
    key = self._EncodeHash(key)
    value = xmlrpclib.Binary(value)
    if secret:
      secret = self._EncodeHash(secret)
      return self.server.put_removable(key, value, 'SHA', secret, ttl, APP_ID)
    return self.server.put(key, value, ttl, APP_ID)

  def GetDetails(self, key, max_values=1, placemark=''):
    key = self._EncodeHash(key)
    placemark = xmlrpclib.Binary(placemark)
    return self.server.get_details(key, max_values, placemark, APP_ID)

  def Get(self, key, max_values=1, placemark=''):
    key = self._EncodeHash(key)
    placemark = xmlrpclib.Binary(placemark)
    values, placemark = self.server.get(key, max_values, placemark, APP_ID)
    values = [v.data for v in values]
    placemark = placemark.data
    return values, placemark

  def GetAll(self, key, max_values=5):
    key = self._EncodeHash(key)
    values, placemark = self.Get(key, max_values)
    while not placemark:
      new_values, placemark = self.Get(key, max_values, placemark)
      values.extend(new_values)

  def Remove(self, key, value, secret, ttl=TTL):
    key = self._EncodeHash(key)
    value = self._EncodeHash(value)
    secret = self._EncodeHash(secret)
    return self.server.rm(key, value, 'SHA', secret, ttl, APP_ID)
