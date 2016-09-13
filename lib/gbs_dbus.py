#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import dbus
import dbus.service

################################################################################
# DBus API Docs
################################################################################
#
# ==== Main Application ====
# Service             org.fpemud.GentooBuildServer
# Interface           org.fpemud.GentooBuildServer
# Object path         /
#
# Methods:
# void                AddMachine(userName:str, machineName:str)
# void                RemoveMachine(userName:str, machineName:str)
#
# ==== Peer ====
# Service             org.fpemud.GentooBuildServer
# Interface           org.fpemud.GentooBuildServer.Machine
# Object path         /Users/{userName:str}/Machines/{machineName:str}
#
# Methods:
# bool                IsActive()
# str                 GetSshKey()
#


class DbusMainObject(dbus.service.Object):

    def __init__(self, param):
        self.param = param

        # register dbus object path
        bus_name = dbus.service.BusName('org.fpemud.GentooBuildServer', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/org/fpemud/GentooBuildServer')

    def release(self):
        self.remove_from_connection()

    @dbus.service.method('org.fpemud.GentooBuildServer', in_signature='ss', out_signature='')
    def AddMachine(self, userName, machineName):
        dirname = os.path.join(self.param.varDir, userName, machineName)
        if os.path.exists(dirname):
            raise Exception("the specified machine already exists")

    @dbus.service.method('org.fpemud.GentooBuildServer', in_signature='', out_signature='ai')
    def RemoveMachine(self):
        dir1 = os.path.join(self.param.varDir, userName)
        dir2 = os.path.join(dir1, machineName)

        if os.path.exists(dir2):
            GbsUtil.forceDelete(dir2)
        if os.path.exists(dir1):
            if len(os.listdir(dir1)) == 0:
                os.unlink(dir1)

    @dbus.service.method('org.fpemud.SelfNet', in_signature='s', out_signature='i')
    def GetPeer(self, peerName):
        for po in self.peerList:
            if peerName == po.peerName:
                return po.peerId
        return -1

    @dbus.service.signal('org.fpemud.SelfNet', signature='s')
    def WorkStateChanged(self, newWorkState):
        pass

    @dbus.service.method('org.fpemud.SelfNet', in_signature='', out_signature='a{s(ss)}')
    def DebugGetModuleInfo(self):
        return self.param.localManager.debugGetModuleInfo()


class DbusPeerObject(dbus.service.Object):

    def __init__(self, param, peerId, peerName):
        self.param = param
        self.peerId = peerId
        self.peerName = peerName

        # register dbus object path
        bus_name = dbus.service.BusName('org.fpemud.SelfNet', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, '/org/fpemud/SelfNet/Peers/%d' % (self.peerId))

    def release(self):
        self.remove_from_connection()

    @dbus.service.method('org.fpemud.SelfNet.Peer', sender_keyword='sender', in_signature='', out_signature='s')
    def GetName(self, sender=None):
        return self.peerName

    @dbus.service.method('org.fpemud.SelfNet.Peer', sender_keyword='sender', in_signature='', out_signature='s')
    def GetPowerState(self, sender=None):
        powerStateDict = {
            SnPeerManager.POWER_STATE_UNKNOWN: "unknown",
            SnPeerManager.POWER_STATE_POWEROFF: "poweroff",
            SnPeerManager.POWER_STATE_REBOOTING: "rebooting",
            SnPeerManager.POWER_STATE_SUSPEND: "suspend",
            SnPeerManager.POWER_STATE_HIBERNATE: "hibernate",
            SnPeerManager.POWER_STATE_HYBRID_SLEEP: "hybrid-sleep",
            SnPeerManager.POWER_STATE_RUNNING: "running",
        }
        powerState = self.param.peerManager.getPeerPowerState(self.peerName)
        return powerStateDict[powerState]

    @dbus.service.method('org.fpemud.SelfNet.Peer', sender_keyword='sender', in_signature='s', out_signature='', async_callbacks=('reply_handler', 'error_handler'))
    def DoPowerOperation(self, opName, reply_handler, error_handler, sender=None):
        if opName not in ["poweron", "poweroff", "reboot", "wakeup", "suspend", "hibernate", "hybrid-sleep"]:
            error_handler(Exception("invalid power operation name \"%s\"" % (opName)))
            return
        self.param.peerManager.doPeerPowerOperationAsync(self.peerName, str(opName), reply_handler, error_handler)

    @dbus.service.signal('org.fpemud.SelfNet.Peer', signature='s')
    def PowerStateChanged(self, newPowerState):
        pass
