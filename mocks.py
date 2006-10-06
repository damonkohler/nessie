"""Mock objects for testing.

@author: Damon Kohler (me@damonkohler.com)

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
