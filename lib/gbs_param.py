#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class GbsParam:

    def __init__(self):
        self.user = "root"              # fixme
        self.group = "root"             # fixme

        self.libDir = "/usr/lib/syncupd"
        self.runDir = "/run/syncupd"
        self.varDir = "/var/syncupd"
        self.cacheDir = "/var/cache/syncupd"
        self.logDir = "/var/log/syncupd"

        self.certFile = os.path.join(self.varDir, "cert.pem")
        self.privkeyFile = os.path.join(self.varDir, "privkey.pem")

        self.keySize = 1024
        self.imageSizeUnit = 1024 * 1024 * 1024                         # 1GB
        self.maxImageSize = 500                                         # 500GB
        self.defaultImageSize = 50                                      # 50GB

        self.ctrlPort = 2108
        self.pidFile = os.path.join(self.runDir, "syncupd.pid")
        self.logLevel = None
        self.tmpDir = None
        self.machineList = []
