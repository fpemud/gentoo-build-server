#!/usr/bin/env python2

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from twisted.cred import portal
from twisted.conch import avatar
from twisted.conch.checkers import UNIXPasswordDatabase
from twisted.conch.ssh import factory, userauth, connection, keys, session
from twisted.internet import reactor, protocol
from twisted.python import log
from zope.interface import implements


if __name__ == '__main__':
    obj = userauth.SSHUserAuthServer()
    print(obj.name)
    print(obj.method)
    print(obj.authenticatedWith)
    print(obj.supportedAuthentications)
