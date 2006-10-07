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

"""Mock objects for testing.

@author: Damon Kohler
@contact: me@damonkohler.com
@license: MIT License
@copyright: 2006 Damon Kohler

"""

__author__ = "Damon Kohler (me@damonkohler.com)"

from twisted.internet import defer


class MockRemotePeer(object):
    
    def __init__(self):
        self.broker = MockBroker()
        self.remote_calls = []
        self.deferred = defer.Deferred()

    def callRemote(self, *args, **kwargs):
        self.remote_calls.append((args, kwargs))
        return self.deferred


class MockBroker(object):
    
    disconnected = 0


class MockFile(object):
    
    def __init__(self):
        self.read_lines = []
        self.write_lines = []
        self.read_cursor = 0

    def write(self, msg):
        self.write_lines.append(msg)

    def readline(self):
        line = self.read_lines[self.read_cursor]
        self.read_cursor += 1
        return line

    def seek(self, index):
        self.read_cursor = index


class MockPeer(object): pass


class MockTime(object):
    
    def __init__(self, what_time):
        self.what_time = what_time

    def time(self):
        return self.what_time
