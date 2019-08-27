#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class GbsParam:

    def __init__(self):
        self.user = "root"              # fixme
        self.group = "root"             # fixme

        self.libDir = "/usr/lib64/syncupd"
        self.runDir = "/run/syncupd"
        self.varDir = "/var/lib/syncupd"
        self.cacheDir = "/var/cache/syncupd"
        self.logDir = "/var/log/syncupd"

        self.certFile = os.path.join(self.varDir, "cert.pem")
        self.privkeyFile = os.path.join(self.varDir, "privkey.pem")

        self.keySize = 1024

        self.imageSizeInit = 10 * 1024          # 10GB
        self.imageSizeStep = 10 * 1024          # 10GB
        self.imageSizeMinimalRemain = 1 * 1024  # 1GB

        self.ctrlPort = 2108
        self.pidFile = os.path.join(self.runDir, "syncupd.pid")
        self.logLevel = None
        self.tmpDir = None
        self.machineList = []
