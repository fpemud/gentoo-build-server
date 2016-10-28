#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import subprocess
from gbs_util import GbsUtil


class SshService:

    def __init__(self, param, uuid, srcIp, srcCert, rootDir, cmdPatternAllowed):
        self.param = param
        self.rootDir = rootDir

        self.cfgf = os.path.join(self.param.tmpDir, uuid + "-sshd.conf")
        self.proc = None

    def start(self):
        try:
            self.port = GbsUtil.getFreeTcpPort()

            buf = ""
            buf += "ListenAddress :%d\n" % (self.port)
            buf += "HostCertificate \"%s\"" % (self.param.certFile)
            buf += "HostKey \"%s\"" % (self.param.privkeyFile)
            buf += "ChrootDirectory \"%s\"" % (self.rootDir)
            with open(self.cfgf, "w") as f:
                f.write(buf)

            cmd = ""
            cmd += "/usr/sbin/sshd -D -f \"%s\"" % (self.cfgf)
            self.proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)
        except:
            self.stop()
            raise

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            self.proc.wait()
        GbsUtil.forceDelete(self.cfgf)

    def getPort(self):
        return self.port
