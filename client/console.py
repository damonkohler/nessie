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

"""Nessie console client.

@author: Damon Kohler
@contact: nessie@googlegroups.com
@license: MIT License
@copyright: 2006 Damon Kohler

"""

__author__ = "Damon Kohler (nessie@googlegroups.com)"

import sys

import zope.interface

from twisted.internet import interfaces
from twisted.spread import pb
from twisted.python import log


class ConsoleInput(object):
    
    zope.interface.implements(interfaces.IReadDescriptor)
    input_file = sys.stdin

    def __init__(self, peer):
        self.peer = peer

    def fileno(self):
        return 0

    def connectionLost(self, reason):
        print "Lost connection because %s" % reason

    def doRead(self):
        line = self.input_file.readline().strip()
        if line:
            if line[0] == '/':
                self.ParseCommand(line)
            else:
                self.peer.Say(line)
        else:
            # This is for testing only. doRead doesn't need to return anything.
            return None

    def ParseCommand(self, line):
        tokens = line.split(' ')
        command = tokens[0][1:]
        args = tokens[1:]

        method = getattr(self.peer, "client_%s" % command, None)
        if method is None:
            log.msg("No such command: /%s" % command)
        else:
            try:
                state = method(*args)
            except TypeError:
                log.msg("/%s didn't accept arguments %s" % (command, args))
        
    # TODO(damonkohler): Find out why this is necessary.
    def logPrefix(self):
        return 'ConsoleInput'
