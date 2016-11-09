#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import shutil


class PluginObject:

    def __init__(self, param, api):
        self.param = param
        self.api = api
        self.mode = None

    def init_handler(self, requestObj):
        if "mode" not in requestObj:
            raise self.api.ProtocolException("Missing \"mode\" in init command")
        if requestObj["mode"] not in ["fpemud-refsystem-update"]:
            raise self.api.ProtocolException("Invalid \"mode\" in init command")
        self.mode = requestObj["mode"]

    def stage_2_start_handler(self):
        self._check_root()
        self.api.prepareRoot()
        self.sshServ = self.api.SshService(self.param, self.api.getUuid(), self.api.getIpAddress(),
                                           self.api.getCertificate(), self.api.getRootDir(), [])
        self.sshServ.start()
        return {
            "ssh-port": self.sshServ.getPort(),
            "ssh-key": self.sshServ.getKey(),
        }

    def stage_2_end_handler(self):
        if hasattr(self, "sshServ"):
            self.sshServ.stop()
            del self.sshServ
        self.api.unPrepareRoot()

    def stage_3_start_handler(self):
        self._remove_var_files()
        self._check_root()
        self.rsyncServ = self.api.RsyncService(self.param, self.api.getUuid(), self.api.getIpAddress(),
                                               self.api.getCertificate(), self.api.getRootDir(), False)
        self.rsyncServ.start()
        return {"rsync-port": self.rsyncServ.getPort()}

    def stage_3_end_handler(self):
        if hasattr(self, "rsyncServ"):
            self.rsyncServ.stop()
            del self.rsyncServ

    def disconnect_handler(self):
        pass

    def _check_root(self):
        # (code is ugly)
        # should contain and ONLY contain the following directories:
        # "/bin", "/etc", "/lib", "/lib32", "/lib64", "/opt", "/sbin", "/usr", "/var/cache/edb", "/var/db/pkg", "/var/lib/portage", "/var/portage"

        flist = os.listdir(self.api.getRootDir())
        for f in ["bin", "etc", "lib", "opt", "sbin", "usr", "var"]:
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
        for f in ["db", "lib", "portage"]:
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

    def _remove_var_files(self):
        # (code is ugly)
        # remove anything in /var except "/var/cache/edb", "/var/db/pkg", "/var/lib/portage", "/var/portage"

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var"))
        for f in ["cache", "db", "lib", "portage"]:
            flist.remove(f)
        for f in flist:
            shutil.rmtree(os.path.join(self.api.getRootDir(), "var", f))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "cache"))
        flist.remove("edb")
        for f in flist:
            shutil.rmtree(os.path.join(self.api.getRootDir(), "var", "cache", f))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "db"))
        flist.remove("pkg")
        for f in flist:
            shutil.rmtree(os.path.join(self.api.getRootDir(), "var", "db", f))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "lib"))
        flist.remove("portage")
        for f in flist:
            shutil.rmtree(os.path.join(self.api.getRootDir(), "var", "lib", f))
