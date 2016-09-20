#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class GbsParam:

    def __init__(self):
        self.user = "root"              # fixme
        self.group = "root"             # fixme

        self.libDir = "/usr/lib/sync-up-daemon"
        self.runDir = "/run/sync-up-daemon"
        self.varDir = "/var/sync-up-daemon"
        self.cacheDir = "/var/cache/sync-up-daemon"
        self.logDir = "/var/log/sync-up-daemon"

        self.pidFile = os.path.join(self.runDir, "sync-up-daemon.pid")

        self.certFile = os.path.join(self.varDir, "cert.pem")
        self.privkeyFile = os.path.join(self.varDir, "privkey.pem")

        self.logLevel = None            # enum
        self.tmpDir = None
        self.machineList = []

    @property
    def webRootDir(self):
        return os.path.join(self.tmpDir, "webroot")
