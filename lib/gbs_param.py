#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os


class GbsConst:

    user = "root"              # fixme
    group = "root"             # fixme

    libDir = "/usr/lib64/syncupd"
    pluginsDir = os.path.join(libDir, "plugins")
    runDir = "/run/syncupd"
    varDir = "/var/lib/syncupd"

    keySize = 1024

    imageSizeInit = 10 * 1024          # 10GB
    imageSizeStep = 10 * 1024          # 10GB
    imageSizeMinimalRemain = 1 * 1024  # 1GB

    avahiSupport = True


class GbsParam:

    def __init__(self):
        self.cacheDir = "/var/cache/syncupd"
        self.logDir = "/var/log/syncupd"
        self.tmpDir = None

        self.certFile = os.path.join(GbsConst.varDir, "cert.pem")
        self.privkeyFile = os.path.join(GbsConst.varDir, "privkey.pem")

        self.ctrlPort = 2108
        self.pidFile = os.path.join(GbsConst.runDir, "syncupd.pid")
        self.logLevel = None
