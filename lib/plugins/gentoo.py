#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import shutil
import multiprocessing


class PluginObject:

    def __init__(self, param, api):
        self.param = param
        self.api = api
        self.resolvConfFile = os.path.join(self.api.getRootDir(), "etc/resolv.conf")
        self.makeConfFile = os.path.join(self.api.getRootDir(), "etc/portage/make.conf")
        self.oriMakeConfContent = None

    def init_handler(self, requestObj):
        pass

    def stage_2_start_handler(self):
        self._check_root()
        self._prepare_root()
        rsyncPort = self.api.startSyncDownService()
        sshPort, sshKey = self.api.startSshService(["emerge *"])
        return {
            "rsync-port": rsyncPort,
            "ssh-port": sshPort,
            "ssh-key": sshKey,
        }

    def stage_2_end_handler(self):
        self.api.stopSshService()
        self.api.stopSyncDownService()
        self._unprepare_root()

    def disconnect_handler(self):
        pass

    def _check_root(self):
        # should contain the following directories:
        # "/bin", "/etc", "/lib", "/opt", "/sbin", "/usr", "/var/db/pkg", "/var/lib/portage"
        # should NOT contain the following files or directories:
        # "/etc/resolv.conf", "/home", "/root"

        for f in ["bin", "etc", "lib", "opt", "sbin", "usr", "var/db/pkg", "/var/lib/portage"]:
            if not os.path.exists(os.path.join(self.api.getRootDir(), f)):
                raise self.api.BusinessException("File or directory /%s is not synced up" % (f))

        for f in ["etc/resolv.conf", "home", "root"]:
            if os.path.exists(os.path.join(self.api.getRootDir(), f)):
                raise self.api.BusinessException("Redundant file or directory /%s is synced up" % (f))

    def _prepare_root(self):
        self.api.prepareRoot()
        shutil.copyfile("/etc/resolv.conf", self.resolvConfFile)
        if True:
            with open(self.makeConfFile, "r") as f:
                self.oriMakeConfContent = f.read()
            self._updateParallelism()

    def _unprepare_root(self):
        with open(self.makeConfFile, "w") as f:
            f.write(self.oriMakeConfContent)
            self.oriMakeConfContent = None
        os.unlink(self.resolvConfFile)
        self.api.unPrepareRoot()

    def _updateParallelism(self):
        memsize = self._getPhysicalMemorySize()
        ejobnum = max(memsize / 2, 1)

        # work on MAKEOPTS variable
        # for bug 559064 and 592660, we need to add -j and -l, it sucks
        value = self._getMakeConfVar("MAKEOPTS")
        m = re.search(" *-j[0-9]+\\b", value)
        if m is not None:
            value = value.replace(m.group(0), "")
        m = re.search(" *-l[0-9]+\\b", value)
        if m is not None:
            value = value.replace(m.group(0), "")
        m = re.search("--jobs(=([0-9]+))?\\b", value)
        if m is None:
            value += " --jobs=%d" % (multiprocessing.cpu_count())
        else:
            value = value.replace(m.group(0), "--jobs=%d" % (multiprocessing.cpu_count()))
        m = re.search("--load-average(=([0-9\\.]+))?\\b", value)
        if m is None:
            value += " --load-average=%d" % (multiprocessing.cpu_count())
        else:
            value = value.replace(m.group(0), "--load-average=%d" % (multiprocessing.cpu_count()))
        value += " -j%d -l%d" % (multiprocessing.cpu_count(), multiprocessing.cpu_count())
        self._setMakeConfVar("MAKEOPTS", value.lstrip())

        # work on EMERGE_DEFAULT_OPTS variable
        value = self._getMakeConfVar("EMERGE_DEFAULT_OPTS")
        m = re.search("--jobs(=([0-9]+))?\\b", value)
        if m is None:
            value += " --jobs=%d" % (ejobnum)
        else:
            value = value.replace(m.group(0), "--jobs=%d" % (ejobnum))
        m = re.search("--load-average(=([0-9\\.]+))?\\b", value)
        if m is None:
            value += " --load-average=%d" % (multiprocessing.cpu_count())
        else:
            value = value.replace(m.group(0), "--load-average=%d" % (multiprocessing.cpu_count()))
        self._setMakeConfVar("EMERGE_DEFAULT_OPTS", value.lstrip())

    def _getMakeConfVar(self, varName):
        """Returns variable value, returns "" when not found
           Multiline variable definition is not supported yet"""

        buf = ""
        with open(self.makeConfFile, 'r') as f:
            buf = f.read()

        m = re.search("^%s=\"(.*)\"$" % (varName), buf, re.MULTILINE)
        if m is None:
            return ""
        varVal = m.group(1)

        while True:
            m = re.search("\${(\S+)?}", varVal)
            if m is None:
                break
            varName2 = m.group(1)
            varVal2 = self._getMakeConfVar(self.makeConfFile, varName2)
            if varVal2 is None:
                varVal2 = ""

            varVal = varVal.replace(m.group(0), varVal2)

        return varVal

    def _setMakeConfVar(self, varName, varValue):
        """Create or set variable in make.conf
           Multiline variable definition is not supported yet"""

        endEnter = False
        buf = ""
        with open(self.makeConfFile, 'r') as f:
            buf = f.read()
            if buf[-1] == "\n":
                endEnter = True

        m = re.search("^%s=\"(.*)\"$" % (varName), buf, re.MULTILINE)
        if m is not None:
            newLine = "%s=\"%s\"" % (varName, varValue)
            buf = buf.replace(m.group(0), newLine)
            with open(self.makeConfFile, 'w') as f:
                f.write(buf)
        else:
            with open(self.makeConfFile, 'a') as f:
                if not endEnter:
                    f.write("\n")
                f.write("%s=\"%s\"\n" % (varName, varValue))

    def _getPhysicalMemorySize():
        with open("/proc/meminfo", "r") as f:
            # We return memory size in GB.
            # Since the memory size shown in /proc/meminfo is always a
            # little less than the real size because various sort of
            # reservation, so we do a "+1"
            m = re.search("^MemTotal:\\s+(\\d+)", f.read())
            return int(m.group(1)) / 1024 / 1024 + 1
