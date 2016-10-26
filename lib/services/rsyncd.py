#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


class RsyncService:

    def __init__(self, param, uuid, srcIp, srcCert, rootDir, upOrDown):
        self.param = param
        self.uuid = uuid
        self.srcIp = srcIp
        self.srcCert = srcCert
        self.rootDir = rootDir
        self.upOrDown = upOrDown

        self.rsyncdCfgFile = os.path.join(self.param.tmpDir, uuid + "-rsyncd.conf")
        self.stunnelClientCertFile = os.path.join(self.param.tmpDir, uuid + "-cert.pem")
        self.stunnelCfgFile = os.path.join(self.param.tmpDir, uuid + "-stunnel.conf")

        self.port = None

    def start(self):
        self._genRsyncdConf()
        self._genStunnelClientCert()
        self._genStunnelConf()

        self.port = GbsUtil.getFreeTcpPort()
        

    def stop(self):
        os.unlink(self.stunnelCfgFile)
        os.unlink(self.stunnelClientCertFile)
        os.unlink(self.rsyncdCfgFile)

    def getPort(self):
        return self.port

    def _genRsyncdConf(self):
        buf = ""
        buf += "syslog facility = local5\n"
        buf += "use chroot = yes\n"
        buf += "uid = root\n"
        buf += "git = root\n"
        buf += "max connections = 10\n"
        buf += "timeout = 600\n"
        buf += "read only = yes\n"                      # fixme
        buf += "\n"
        buf += "[main]\n"
        buf += "path = %s\n" % (self.rootDir)
        buf += "hosts allow = %s\n" % (self.srcIp)
        buf += "read only = yes\n"                      # fixme
        buf += "ignore nonreadable = yes\n"
        buf += "refuse options = checksum\n"
        buf += "dont compress = *\n"

        with open(self.rsyncdCfgFile, "w") as f:
            f.write(buf)

    def _genStunnelClientCert(self):
        with open(self.stunnelClientCertFile, "wb") as f:
            buf = crypto.dump_certificate(crypto.FILETYPE_PEM, self.srcCert)
            f.write(buf)
            os.fchmod(f.fileno(), 0o644)

    def _genStunnelConf(self):
        buf = ""
        buf += "cert = %s\n" % (self.stunnelClientCertFile)
        buf += "client = no\n"
        buf += "\n"
        buf += "[rsync]\n"
        buf += "accept = 873\n"
        buf += "connect = domain.of.langly.com:273\n"

        with open(self.stunnelCfgFile, "w") as f:
            f.write(buf)