#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class GbsParam:

    def __init__(self):
        self.cfgDir = "/etc/gentoo-build-server"
        self.libDir = "/usr/lib/gentoo-build-server"
        self.runDir = "/run/gentoo-build-server"
        self.varDir = "/var/gentoo-build-server"
        self.logDir = "/var/log/gentoo-build-server"

        self.pidFile = os.path.join(self.runDir, "gentoo-build-server.pid")
        self.logFile = os.path.join(self.logDir, "main.log")
        self.clientDataFile = os.path.join(self.varDir, "client.dat") 

        self.clientTimeoutInterval = 120            # 120 seconds

        self.tmpDir = None              # str
        self.logLevel = None            # enum

        self.mainloop = None
        self.mainObject = None
        self.pyroServer = None
