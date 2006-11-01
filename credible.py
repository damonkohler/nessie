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

"""Provides objects for working with twisted.cred (i.e. Avatar, Realm, etc.).

@author: Damon Kohler
@contact: nessie@googlegroups.com
@license: MIT License
@copyright: 2006 Damon Kohler

"""

__author__ = "Damon Kohler (nessie@googlegroups.com)"

import zope.interface

from twisted.cred import portal, checkers, credentials
from twisted.spread import pb
from twisted.python import util, log


class Loch(object):

    """Realm for serving up peer avatars."""

    zope.interface.implements(portal.IRealm)

    def __init__(self, root_peer):
        self.monsters = {}
        self.root_peer = root_peer

    def requestAvatar(self, avatar_id, mind, *interfaces):
        assert pb.IPerspective in interfaces
        if avatar_id in self.monsters:
            avatar = self.monsters[avatar_id]
        else:
            avatar = LochMonster(avatar_id, self.root_peer)
            self.monsters[avatar_id] = avatar
        avatar_tuple = pb.IPerspective, avatar, lambda a=avatar: a.detached()
        d = avatar.attached(mind)
        if d:
            d.addCallback(lambda unused_arg: avatar_tuple)
            return d
        else:
            return avatar_tuple


class LochMonster(pb.Avatar):

    """Peer avatar."""

    def __init__(self, uuid, root_peer):
        self.uuid = uuid
        self.root_peer = root_peer

    def attached(self, mind):
        self.remote = mind
        if mind is None:
            return False
        return self.root_peer.ReverseAuthenticate(mind)

    def detached(self):
        self.remote = None

    def perspective_AddPeer(self, uuid, peer, direct=False):
        root_peer.AddPeer(uuid, peer, direct=direct)

    def perspective_UpdateRemotePeers(self, update_serial):
        """Initiates a remote peer update.
        
        @todo: If I were using Avatars and views I would know who
        called me and I could avoid sending them updates. This is a
        good idea because I obviously won't know anything more than
        they do.

        """
        log.msg("Asked to do update #%d of remote peers." % update_serial,
                debug=1)
        if update_serial != self.last_update_serial:
            root_peer.last_update_serial = update_serial
            return root_peer.UpdateRemotePeers(update_serial)
        log.msg("Already did update #%d. Skipped." % update_serial, debug=1)

    def perspective_GetUUID(self):
        """Returns the UUID for this server."""
        log.msg("Sending UUID %s." % self.uuid, debug=1)
        return self.root_peer.uuid

    def perspective_GetPeers(self):
        """Returns a list of proxied peers.

        Once a peer has authenticated, they'll want a list of peers
        they can talk to through us. This is where they start.

        """
        return self.root_peer.GetProxyPeers()


class Channel(pb.Referenceable):

    """Communication channel or mind.

    The mind doesn't really need to do much. Since we are
    authenticating in both directions, all we want is to get the IP of
    the peer and the port to connect to. We can get the IP by
    accessing the mind's broker via
    mind.broker.transport.getPeer(). But, we have to ask nicely for
    the port.

    """
    def __init__(self, port, uuid):
        self.port = port
        self.uuid = uuid
        
    def remote_GetPort(self):
        return self.port

    def remote_GetUUID(self):
        return self.uuid


class NoAuthCredentials(credentials.UsernamePassword):

    """Simple credentials that only store a UUID as username."""

    def __init__(self, uuid):
        credentials.UsernamePassword.__init__(self, uuid, '')
    

class NoAuthChecker(checkers.InMemoryUsernamePasswordDatabaseDontUse):

    """Credential checker which simply returns the UUID specified by creds."""

    def requestAvatarId(self, creds):
        return creds.username
