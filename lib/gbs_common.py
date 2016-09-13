#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class GbsCommon:

    @staticmethod
    def isUserNameValid(userName):
        return re.search("^([a-z_][a-z0-9_]+)$", re.I) is not None

    @staticmethod
    def isSystemNameValid(systemName):
        return re.search("^[A-Za-z0-9-_\\.\\(\\)]$") is not None

    @staticmethod
    def addSystem(param, userName, systemName):
        dirname = os.path.join(self.param.varDir, userName, machineName)
        os.makedirs(dirname)
        param.machineList.append(DbusMachineObject(userName, machineName))

    @staticmethod
    def removeSystem(param, userName, systemName):




