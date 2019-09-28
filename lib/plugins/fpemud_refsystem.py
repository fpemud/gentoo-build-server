#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import shutil
import subprocess


class PluginObject:

    def __init__(self, param, api):
        self.param = param
        self.api = api
        self.resolvConfFile = os.path.join(self.api.getRootDir(), "etc/resolv.conf")
        self.makeConfFile = os.path.join(self.api.getRootDir(), "etc/portage/make.conf")

    def stage_working_start_handler(self, requestObj):
        self._check_root()
        self._prepare_root()
        return {}

    def stage_working_end_handler(self):
        self._unprepare_root()

    def _check_root(self):
        if not os.path.exists(self.makeConfFile):
            raise self.api.BusinessException("/etc/portage/make.conf is not synced up")

        for f in ["var/db/pkg", "/var/lib/portage"]:
            if not os.path.exists(os.path.join(self.api.getRootDir(), f)):
                raise self.api.BusinessException("File or directory /%s is not synced up" % (f))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "lib"))
        if "portage" not in flist:
            raise self.api.BusinessException("Directory /var/lib/portage is not synced up")

    def _prepare_root(self):
        if os.path.exists(self.resolvConfFile):
            os.unlink(self.resolvConfFile)
        shutil.copyfile("/etc/resolv.conf", self.resolvConfFile)
        self.__removeMakeConfVar("FPEMUD_REFSYSTEM_BUILD_SERVER")

    def _unprepare_root(self):
        if os.path.exists(self.makeConfFile):
            os.unlink(self.makeConfFile)
        if os.path.exists(self.resolvConfFile):
            os.unlink(self.resolvConfFile)

    def __removeMakeConfVar(self, varName):
        """Remove variable in make.conf
           Multiline variable definition is not supported yet"""

        endEnterCount = 0
        lineList = []
        with open(self.makeConfFile, 'r') as f:
            buf = f.read()
            endEnterCount = len(buf) - len(buf.rstrip("\n"))

            buf = buf.rstrip("\n")
            for l in buf.split("\n"):
                if re.search("^%s=" % (varName), l) is None:
                    lineList.append(l)

        buf = ""
        for l in lineList:
            buf += l + "\n"
        buf = buf.rstrip("\n")
        for i in range(0, endEnterCount):
            buf += "\n"

        with open(self.makeConfFile, 'w') as f:
            f.write(buf)
