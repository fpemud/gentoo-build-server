#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class GbsParam:

    def __init__(self):
        self.user = "root"              # fixme
        self.group = "root"             # fixme

        self.libDir = "/usr/lib/gentoo-build-server"
        self.runDir = "/run/gentoo-build-server"
        self.varDir = "/var/gentoo-build-server"
        self.cacheDir = "/var/cache/gentoo-build-server"
        self.logDir = "/var/log/gentoo-build-server"

        self.pidFile = os.path.join(self.runDir, "gentoo-build-server.pid")

        self.clientPasswdFile = os.path.join(self.varDir, "htpasswd")
        self.clientDataFile = os.path.join(self.varDir, "client.dat")
        self.clientTimeoutInterval = 120                                        # 120 seconds

        self.machineList = []

        self.protocol = None            # "HTTP", "HTTPS", default is "HTTP"
        self.port = None                # for HTTP, default is 80; for HTTPS, default is 443
        self.authType = None            # "NONE", "HTPASSWD", default is "NONE"
        self.logLevel = None            # enum
        self.tmpDir = None

    @property
    def webRootDir(self):
        return os.path.join(self.tmpDir, "webroot")
