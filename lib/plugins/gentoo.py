#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class PluginObject:

    def __init__(self, param, api):
        self.param = param
        self.api = api
        self.mode = None

    def init_handler(self, requestObj):
        if "mode" not in requestObj:
            raise self.api.ProtocolException("Missing \"mode\" in init command")
        if requestObj["mode"] not in ["emerge+sync", "emerge+binpkg"]:
            raise self.api.ProtocolException("Invalid \"mode\" in init command")
        self.mode = requestObj["mode"]

    def stage_2_start_handler(self):
        self._check_root()
        self.api.prepareRoot()
        self.sshServ = self.api.SshService(self.param, self.api.getUuid(), self.api.getIpAddress(),
                                           self.api.getCertificate(), self.api.getRootDir(), ["emerge .*"])
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
        self._check_root()
        if self.mode == "emerge+sync":
            self.rsyncServ = self.api.RsyncService(self.param, self.api.getUuid(), self.api.getIpAddress(),
                                                   self.api.getCertificate(), self.api.getRootDir(), False)
            self.rsyncServ.start()
            return {
                "rsync-port": self.rsyncServ.getPort(),
                "extra-patterns": self._get_extra_patterns(),
            }
        elif self.mode == "emerge+binpkg":
            assert False
        else:
            assert False

    def stage_3_end_handler(self):
        if self.mode == "emerge+sync":
            if hasattr(self, "rsyncServ"):
                self.rsyncServ.stop()
                del self.rsyncServ
        elif self.mode == "emerge+binpkg":
            assert False
        else:
            assert False

    def disconnect_handler(self):
        pass

    def _check_root(self):
        # should contain the following directories:
        # "/bin", "/etc", "/lib", "/opt", "/sbin", "/usr", "/var/db/pkg", "/var/lib/portage"
        # should NOT contain the following directories:
        # "/boot", "/home", "/root"

        for f in ["bin", "etc", "lib", "opt", "sbin", "usr", "var/db/pkg", "/var/lib/portage"]:
            if not os.path.exists(os.path.join(self.api.getRootDir(), f)):
                raise self.api.BusinessException("Directory /%s is not synced up" % (f))

        for f in ["boot", "home", "root"]:
            if os.path.exists(os.path.join(self.api.getRootDir(), f)):
                raise self.api.BusinessException("Redundant directory /%s is synced up" % (f))

    def _get_extra_patterns(self):
        # extra pattern is extra files to sync down, don't do delete for this files

        ret = []

        flist = os.listdir(self.api.getRootDir())
        for f in ["bin", "etc", "lib", "lib32", "lib64", "opt", "sbin", "usr", "var"]:
            try:
                flist.remove(f)
            except ValueError:
                pass            # lib32, lib64 may not exist
        for f in flist:
            fullfn = os.path.join(self.api.getRootDir(), f)
            if os.path.islink(fullfn) or not os.path.isdir(fullfn):
                ret.append("/%s" % (f))
            else:
                ret.append("/%s/***" % (f))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var"))
        for f in ["cache", "db", "lib"]:
            flist.remove(f)
        for f in flist:
            fullfn = os.path.join(self.api.getRootDir(), "var", f)
            if os.path.islink(fullfn) or not os.path.isdir(fullfn):
                ret.append("/var/%s" % (f))
            else:
                ret.append("/var/%s/***" % (f))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "cache"))
        flist.remove("edb")
        for f in flist:
            fullfn = os.path.join(self.api.getRootDir(), "var", "cache", f)
            if os.path.islink(fullfn) or not os.path.isdir(fullfn):
                ret.append("/var/db/%s" % (f))
            else:
                ret.append("/var/db/%s/***" % (f))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "db"))
        flist.remove("pkg")
        for f in flist:
            fullfn = os.path.join(self.api.getRootDir(), "var", "db", f)
            if os.path.islink(fullfn) or not os.path.isdir(fullfn):
                ret.append("/var/db/%s" % (f))
            else:
                ret.append("/var/db/%s/***" % (f))

        flist = os.listdir(os.path.join(self.api.getRootDir(), "var", "lib"))
        flist.remove("portage")
        for f in flist:
            fullfn = os.path.join(self.api.getRootDir(), "var", "lib", f)
            if os.path.islink(fullfn) or not os.path.isdir(fullfn):
                ret.append("/var/lib/%s" % (f))
            else:
                ret.append("/var/lib/%s/***" % (f))

        return ret
