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
        self.oriMakeConfContent = None

    def init_handler(self, requestObj):
        pass

    # stage2: synchronize kernel, gentoo repository and gentoo overlays

    # stage3: download files

    # stage4: fetch files

    # stage5: download files

    # stage6: build kernel
    def stage_2_start_handler(self):
        self._check_root()
        self._prepare_root()
        port, key = self.api.startSshService([])
        return {
            "ssh-port": port,
            "ssh-key": key,
        }

    def stage_2_end_handler(self):
        self.api.stopSshService()
        self._unprepare_root()

    # stage7: download files
    def stage_3_start_handler(self):
        resultFile = os.path.join(self.api.getRootDir(), "result.txt")
        with open(resultFile, "r") as f:
            lines = [x.rstrip() for x in f.readlines()]
            assert len(lines) == 3
        os.unlink(resultFile)

        self._check_root()
        port = self.api.startSyncDownService()
        return {
            "rsync-port": port,
            "kernel-built": bool(lines[0]),
            "verstr": lines[1],
            "postfix": lines[2],
        }

    def stage_3_end_handler(self):
        self.api.stopSyncDownService()

    # stage8: update system
    def stage_4_start_handler(self):
        self._check_root()
        self._prepare_root()
        sshPort, sshKey = self.api.startSshService(["emerge *"])
        return {
            "ssh-port": sshPort,
            "ssh-key": sshKey,
        }

    def stage_4_end_handler(self):
        self.api.stopSshService()
        self._unprepare_root()

    # stage9: download files
    def stage_5_start_handler(self):
        port = self.api.startSyncDownService()
        return {
            "rsync-port": port,
        }

    def stage_5_end_handler(self):
        self.api.stopSyncDownService()

    def disconnect_handler(self):
        pass

    def _check_root(self):
        # (code is ugly)
        # should contain and ONLY contain the following directories:
        # "/bin", "/boot", "/etc", "/lib", "/lib32", "/lib64", "/opt", "/sbin", "/usr", "/var/cache/edb", "/var/db/pkg", "/var/lib/portage", "/var/fpemud-refsystem"
        # should NOT contain the following files or directories:
        # "/etc/resolv.conf"

        flist = os.listdir(self.api.getRootDir())
        for f in ["bin", "boot", "etc", "lib", "opt", "sbin", "usr", "var"]:
            try:
                flist.remove(f)
            except ValueError:
                raise self.api.BusinessException("Directory /%s is not synced up" % (f))
        for f in ["lib32", "lib64"]:
            try:
                flist.remove(f)
            except ValueError:
                pass
        if flist != []:
            raise self.api.BusinessException("Redundant directories %s are synced up" % (",".join(["/" + x for x in flist])))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var"))
        for f in ["db", "lib", "fpemud-refsystem"]:
            try:
                flist.remove(f)
            except ValueError:
                raise self.api.BusinessException("Directory /var/%s is not synced up" % (f))
        for f in ["cache"]:
            try:
                flist.remove(f)
            except ValueError:
                pass
        if flist != []:
            raise self.api.BusinessException("Redundant directories %s are synced up" % (",".join(["/var/" + x for x in flist])))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "db"))
        try:
            flist.remove("pkg")
        except ValueError:
            raise self.api.BusinessException("Directory /var/db/pkg is not synced up")
        if flist != []:
            raise self.api.BusinessException("Redundant directories %s are synced up" % (",".join(["/var/db/" + x for x in flist])))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "lib"))
        try:
            flist.remove("portage")
        except ValueError:
            raise self.api.BusinessException("Directory /var/lib/portage is not synced up")
        if flist != []:
            raise self.api.BusinessException("Redundant directories %s are synced up" % (",".join(["/var/lib/" + x for x in flist])))

        for f in ["etc/resolv.conf"]:
            if os.path.exists(os.path.join(self.api.getRootDir(), f)):
                raise self.api.BusinessException("Redundant file or directory /%s is synced up" % (f))

    def _prepare_root(self):
        self.api.prepareRoot()
        shutil.copyfile("/etc/resolv.conf", self.resolvConfFile)
        if True:
            with open(self.makeConfFile, "r") as f:
                self.oriMakeConfContent = f.read()
            self._removeMakeConfVar("FPEMUD_REFSYSTEM_BUILD_SERVER")
            subprocess.Popen("/usr/bin/chroot \"%s\" /usr/bin/sysman update-parallelism >/dev/null" % (self.api.getRootDir()), shell=True).wait()

    def _unprepare_root(self):
        with open(self.makeConfFile, "w") as f:
            f.write(self.oriMakeConfContent)
            self.oriMakeConfContent = None
        os.unlink(self.resolvConfFile)
        self.api.unPrepareRoot()

    def _removeMakeConfVar(self, varName):
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

    # def _remove_var_files(self):
    #     # (code is ugly)
    #     # remove anything in /var except "/var/cache/edb", "/var/db/pkg", "/var/lib/portage", "/var/portage"

    #     flist = os.listdir(os.path.join(self.api.getRootDir(), "var"))
    #     for f in ["cache", "db", "lib", "portage"]:
    #         flist.remove(f)
    #     for f in flist:
    #         shutil.rmtree(os.path.join(self.api.getRootDir(), "var", f))

    #     flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "cache"))
    #     flist.remove("edb")
    #     for f in flist:
    #         shutil.rmtree(os.path.join(self.api.getRootDir(), "var", "cache", f))

    #     flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "db"))
    #     flist.remove("pkg")
    #     for f in flist:
    #         shutil.rmtree(os.path.join(self.api.getRootDir(), "var", "db", f))

    #     flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "lib"))
    #     flist.remove("portage")
    #     for f in flist:
    #         shutil.rmtree(os.path.join(self.api.getRootDir(), "var", "lib", f))
