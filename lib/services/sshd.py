#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import subprocess
from gbs_util import GbsUtil


class SshService:

    def __init__(self, param, uuid, srcIp, srcCert, rootDir):
        self.param = param
        self.rootDir = rootDir

        self.logLevelDict = {
            'CRITICAL': "FATAL",
            'ERROR': "ERROR",
            'WARNING': "ERROR",
            'INFO': "INFO",
            'DEBUG': "DEBUG",
        }

        self.cfgf = os.path.join(self.param.tmpDir, uuid + "-sshd.conf")
        # self.certf = os.path.join(self.param.tmpDir, uuid + "-cert.openssh")
        self.certf = os.path.join(self.param.tmpDir, uuid + "-key.openssh-cert.pub")        # fixme
        self.keyf = os.path.join(self.param.tmpDir, uuid + "-key.openssh")
        self.akeyf = os.path.join(self.param.tmpDir, uuid + "-authorized_keys")
        self.proc = None

    def start(self):
        try:
            # fixme: generate new cert and key for openssh
            # should convert self.param.cert and self.param.key to openssh format
            GbsUtil.shell("/usr/bin/ssh-keygen -q -N \"\" -f %s" % (self.keyf))
            GbsUtil.shell("/usr/bin/ssh-keygen -q -h -I abc -V +1w -s %s %s" % (self.keyf, self.keyf))
            GbsUtil.shell("/bin/cp %s.pub %s" % (self.keyf, self.akeyf))
            GbsUtil.shell("/bin/cp %s.pub %s" % (self.keyf, "/root/.ssh/authorized_keys"))

            self.port = GbsUtil.getFreeTcpPort()

            buf = ""
            buf += "LogLevel %s\n" % (self.logLevelDict[self.param.logLevel])
            buf += "\n"
            buf += "ListenAddress 0.0.0.0:%d\n" % (self.port)
            buf += "HostCertificate \"%s\"\n" % (self.certf)
            buf += "HostKey \"%s\"\n" % (self.keyf)
#            buf += "AuthorizedKeysFile \"%s\"" % (self.akeyf)
            buf += "ChrootDirectory \"%s\"\n" % (self.rootDir)
            buf += "\n"
            buf += "PermitRootLogin yes\n"
            buf += "PasswordAuthentication no\n"
            buf += "KbdInteractiveAuthentication no\n"
            buf += "ChallengeResponseAuthentication no\n"
#            buf += "PubkeyAuthentication no\n"
            buf += "AuthenticationMethods \"publickey\"\n"
            with open(self.cfgf, "w") as f:
                f.write(buf)

            cmd = ""
            cmd += "/usr/sbin/sshd -D -f \"%s\"" % (self.cfgf)
            self.proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

            GbsUtil.waitTcpPort(self.port)
        except:
            self.stop()
            raise

    def stop(self):
        if self.proc is not None:
            self.proc.terminate()
            self.proc.wait()
        GbsUtil.forceDelete(self.akeyf)
        GbsUtil.forceDelete(self.keyf)
        GbsUtil.forceDelete(self.certf)
        GbsUtil.forceDelete(self.cfgf)

    def getPort(self):
        return self.port

    def getKey(self):
        with open(self.keyf) as f:
            return f.read()

#$ scp foobar.example.org:/etc/ssh/ssh_host_rsa_key.pub foobar.pub
#$ ssh-keygen -h                             \ # sign host key
#             -s ~/.ssh/cert_signer          \ # CA key
#             -I foobar                      \ # Key identifier
#             -V +1w                         \ # Valid only 1 week
#             -n foobar,foobar.example.org   \ # Valid hostnames
#             foobar.pub                       # Host pubkey file
#$ scp foobar-cert.pub foobar.example.org:/etc/ssh/ssh_host_rsa_key-cert.pub
