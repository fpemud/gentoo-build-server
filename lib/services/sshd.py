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
        self.certf = os.path.join(self.param.tmpDir, uuid + "-cert.pem")
        self.keyf = os.path.join(self.param.tmpDir, uuid + "-authorized_keys")
        self.proc = None

    def start(self):
        try:
            self.port = GbsUtil.getFreeTcpPort()

            buf = ""
            buf += "ssh-rsa
            srcCert..get_pubkey()
            
            
            AAAAB3NzaC1yc2EAAAADAQABAAABAQDJuswSBK9VgIJddzClfZnxHCBzhhFv+iHh9LxbifKDZO1r/IyHp0ySJVl1l2Wpxu7KNw/CCGM6RujJyDfXUoVjWuobkqtrQaFoCNnQQaEeraSyujRxUZO+1mOxPK04BncfF7jMRyJgU4mzEIOvDEgGbVNRh78+8Alf2Eg5fgWYhRrvGt1v7B1/l/L7T2Ky/Wm65TURXZ6XY/k91Yz/0U9pwujrvowTYtcDSjV1lyTfsMdVN3Jv6KlI3WYoJvgky5vTOX/qNeFLTMOagN5Ur5TQKksDVnDo+LqPfBPy3wl8WJV1ip85rRt971yLGqo+SJ+rOqNRy2mwQmDUB1fbTF root@fpemud-workstation
"


            buf = ""
            buf += "ListenAddress 0.0.0.0:%d\n" % (self.port)
            buf += "HostCertificate \"%s\"\n" % (self.param.certFile)
            buf += "HostKey \"%s\"\n" % (self.param.privkeyFile)
            buf += "AuthorizedKeysFile \"%s\"" % ()
            buf += "ChrootDirectory \"%s\"\n" % (self.rootDir)
            buf += "\n"
            buf += "PermitRootLogin forced-commands-only\n"
            buf += "PasswordAuthentication no\n"
            buf += "KbdInteractiveAuthentication no\n"
            buf += "ChallengeResponseAuthentication no\n"
            buf += "AuthenticationMethods \"publickey\"\n"
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
