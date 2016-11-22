#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class PluginObject:

    def __init__(self, param, api):
        self.param = param
        self.api = api

    def init_handler(self, requestObj):
        pass

    def stage_2_start_handler(self):
        self._check_root()
        self.api.prepareRoot()
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
        self.api.unPrepareRoot()

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