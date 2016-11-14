#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import subprocess
from gbs_util import GbsUtil


class RsyncService:

    def __init__(self, param, uuid, srcIp, srcCert, rootDir, upOrDown):
        self.param = param
        self.uuid = uuid
        self.srcIp = srcIp
        self.srcCert = srcCert
        self.rootDir = rootDir
        self.upOrDown = upOrDown

        self.rsyncdCfgFile = os.path.join(self.param.tmpDir, uuid + "-rsyncd.conf")
        self.rsyncdLogFile = os.path.join(self.param.logDir, uuid + "-rsyncd.log")
        self.stunnelClientCertFile = os.path.join(self.param.tmpDir, uuid + "-cert.pem")
        self.stunnelCfgFile = os.path.join(self.param.tmpDir, uuid + "-stunnel.conf")
        self.stunnelRndFile = os.path.join(self.param.tmpDir, uuid + "-stunnel.rnd")
        self.stunnelLogFile = os.path.join(self.param.logDir, uuid + "-stunnel.log")

        self.rsyncPort = None
        self.stunnelPort = None

        self.rsyncProc = None
        self.stunnelProc = None

    def start(self):
        try:
            self.rsyncPort = GbsUtil.getFreeTcpPort()
            self.stunnelPort = GbsUtil.getFreeTcpPort()

            self.rsyncProc = self._runRsyncDeamon()
            self.stunnelProc = self._runStunnelDaemon()

            GbsUtil.waitTcpPort(self.rsyncPort)
            GbsUtil.waitTcpPort(self.stunnelPort)
        except:
            self.stop()
            raise

    def stop(self):
        if self.stunnelProc is not None:
            self.stunnelProc.terminate()
            self.stunnelProc.wait()
        if self.rsyncProc is not None:
            self.rsyncProc.terminate()
            self.rsyncProc.wait()
        GbsUtil.forceDelete(self.stunnelRndFile)
        GbsUtil.forceDelete(self.stunnelCfgFile)
        GbsUtil.forceDelete(self.stunnelClientCertFile)
        GbsUtil.forceDelete(self.rsyncdCfgFile)

    def getPort(self):
        return self.stunnelPort

    # def _genStunnelClientCert(self):
    #     with open(self.stunnelClientCertFile, "wb") as f:
    #         buf = crypto.dump_certificate(crypto.FILETYPE_PEM, self.srcCert)
    #         f.write(buf)
    #         os.fchmod(f.fileno(), 0o644)

    def _runRsyncDeamon(self):
        buf = ""
        buf += "log file = %s\n" % (self.rsyncdLogFile)
        buf += "\n"
        buf += "port = %s\n" % (self.rsyncPort)
        buf += "max connections = 1\n"
        buf += "timeout = 600\n"
        buf += "hosts allow = 127.0.0.1\n"
        buf += "\n"
        buf += "use chroot = yes\n"
        buf += "uid = root\n"
        buf += "gid = root\n"
        buf += "\n"
        buf += "[main]\n"
        buf += "path = %s\n" % (self.rootDir)
        buf += "read only = %s\n" % ("no" if self.upOrDown else "yes")
        with open(self.rsyncdCfgFile, "w") as f:
            f.write(buf)

        cmd = ""
        cmd += "/usr/bin/rsync --daemon --no-detach --config=\"%s\"" % (self.rsyncdCfgFile)
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)
        return proc

    def _runStunnelDaemon(self):
        buf = ""
        buf += "debug = 6\n"
        buf += "output = %s\n" % (self.stunnelLogFile)
        buf += "\n"
        buf += "cert = %s\n" % (self.param.certFile)
        buf += "key = %s\n" % (self.param.privkeyFile)
        buf += "RNDfile = %s\n" % (self.stunnelRndFile)
        buf += "\n"
        buf += "client = no\n"
        buf += "foreground = yes\n"
        buf += "\n"
        buf += "[rsync]\n"
        buf += "accept = 0.0.0.0:%d\n" % (self.stunnelPort)
        buf += "connect = 127.0.0.1:%d\n" % (self.rsyncPort)
        with open(self.stunnelCfgFile, "w") as f:
            f.write(buf)

        cmd = ""
        cmd += "/usr/sbin/stunnel \"%s\"" % (self.stunnelCfgFile)
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)
        return proc
