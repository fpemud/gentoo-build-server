#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import dbus
import dbus.service


################################################################################
# DBus API Docs
################################################################################
#
# ==== Main Application ====
# Service               org.fpemud.GentooBuildServer
# Interface             org.fpemud.GentooBuildServer
# Object path           /
#
# Methods:
# bool                     IsUp()
# str                      GetInterface()
# array<str>               GetNameServerList()
# array<ip,mask>           GetPrefixList()
# array<ip,domain-name>    GetDnsEntryList()
#
# Signals:
#                           DataChanges()

class DbusMainObject(dbus.service.Object):

    def __init__(self, param):
        self.param = param

        # register dbus object path
        bus_name = dbus.service.BusName('org.fpemud.CGFW', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/org/fpemud/CGFW')

    @dbus.service.method('org.fpemud.CGFW', in_signature='', out_signature='s')
    def GetInterface(self):
        return self.param.cgfwCfg.interface

    @dbus.service.method('org.fpemud.CGFW', in_signature='', out_signature='as')
    def GetNameServerList(self):
        return self.param.nameServerList

    @dbus.service.method('org.fpemud.CGFW', in_signature='', out_signature='a(ss)')
    def GetPrefixList(self):
        return CgfwCommon.getPrefixList(self.param.gfwDir, self.param.ngfwDir)

    @dbus.service.method('org.fpemud.CGFW', in_signature='', out_signature='a(ss)')
    def GetDnsEntryList(self):
        return CgfwCommon.getHostsList(self.param.hostsDir)

    @dbus.service.signal('org.fpemud.CGFW', signature='s')
    def DataChanges(self, key):
        pass
