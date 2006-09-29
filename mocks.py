class MockRemotePeer(object):
    def __init__(self):
        self.broker = MockBroker()


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
