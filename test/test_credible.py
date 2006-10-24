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

"""Tests for nessie.credible.

@author: Damon Kohler
@contact: nessie@googlegroups.com
@license: MIT License
@copyright: 2006 Damon Kohler

"""

__author__ = "Damon Kohler (nessie@googlegroups.com)"

from twisted.trial import unittest
from twisted.internet import reactor, defer
from twisted.spread import pb
from twisted.python import util, log

from nessie import credible
from nessie.test import mocks
from nessie.util import curry


class LochTest(unittest.TestCase):
    
    """Tests nessie.credible.Loch."""

    def setUp(self):
        self.p = mocks.MockPeer()
        self.l = credible.Loch(self.p)

    def testInit(self):
        self.assertEqual(self.l.root_peer, self.p)
        self.assertEqual(self.l.monsters, {})

    def testRequestAvatar(self):
        avatar_id = 'id'
        class Mind(object): pass
        self.assertRaises(AssertionError, self.l.requestAvatar, avatar_id, None)
        iface, avatar, f = self.l.requestAvatar(avatar_id, None,
                                                pb.IPerspective)
        self.assert_(iface is pb.IPerspective)
        self.assert_(avatar_id in self.l.monsters)
        iface, avatar_b, f = self.l.requestAvatar(avatar_id, None,
                                                  pb.IPerspective)
        self.assert_(avatar_b is avatar)
