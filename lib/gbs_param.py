#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class SnParam:

    def __init__(self):
        self.cfgDir = "/etc/gentoo-build-server"
        self.libDir = "/usr/lib/gentoo-build-server"
        self.runDir = "/run/gentoo-build-server"
        self.cacheDir = "/var/cache/gentoo-build-server"
        self.logDir = "/var/log/gentoo-build-server"

        self.pidFile = os.path.join(self.runDir, "gentoo-build-server.pid")
        self.logFile = os.path.join(self.logDir, "main.log")

        self.tmpDir = None              # str
        self.logLevel = None            # enum
        self.mainloop = None            # obj
