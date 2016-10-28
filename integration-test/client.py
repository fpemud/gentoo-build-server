#!/usr/bin/env python2
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import socket
import random
import subprocess
import json
from OpenSSL import crypto
from OpenSSL import SSL


class TestClient:

    def __init__(self, certFile, keyFile):
        self.certFile = certFile
        self.keyFile = keyFile
        self.sock = None
        self.sslSock = None

    def connect(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", port))

        ctx = SSL.Context(SSL.SSLv3_METHOD)
        ctx.use_privatekey_file(self.keyFile)
        ctx.use_certificate_file(self.certFile)
        self.sslSock = SSL.Connection(ctx, self.sock)
        self.sslSock.set_connect_state()

    def dispose(self):
        self.sslSock.close()

    def cmdInit(self, cpuArch, size, plugin):
        requestObj = dict()
        requestObj["command"] = "init"
        requestObj["cpu-arch"] = cpuArch
        requestObj["size"] = size
        requestObj["plugin"] = plugin
        requestObj["mode"] = "emerge+sync"
        self.sslSock.send(json.dumps(requestObj) + "\n")
        return self._recvReponseObj(self.sslSock)

    def cmdStage(self):
        requestObj = dict()
        requestObj["command"] = "stage"
        self.sslSock.send(json.dumps(requestObj) + "\n")
        return self._recvReponseObj(self.sslSock)

    def cmdQuit(self):
        requestObj = dict()
        requestObj["command"] = "quit"
        self.sslSock.send(json.dumps(requestObj) + "\n")
        return self._recvReponseObj(self.sslSock)

    def _recvReponseObj(self, sslSock):
        buf = ""
        while True:
            buf += sslSock.recv(4096)
            i = buf.find("\n")
            if i >= 0:
                assert i == len(buf) - 1
                return json.loads(buf[:i])


class TestRsync:

    def __init__(self, certFile, keyFile):
        self.certFile = certFile
        self.keyFile = keyFile

    def syncUp(self, dirname, ip, port):
        proc = self._runStunnelDaemon(ip, port)
        self._runRsync(dirname)
        proc.terminate()
        proc.wait()
        os.unlink("./stunnel.conf")

    def _runStunnelDaemon(self, ip, port):
        buf = ""
        buf += "cert = %s\n" % (self.certFile)
        buf += "key = %s\n" % (self.keyFile)
        buf += "\n"
        buf += "client = yes\n"
        buf += "foreground = yes\n"
        buf += "\n"
        buf += "[rsync]\n"
        buf += "accept = 127.0.0.1:874\n"
        buf += "connect = %s:%d\n" % (ip, port)

        with open("./stunnel.conf", "w") as f:
            f.write(buf)

        cmd = ""
        cmd += "/usr/sbin/stunnel ./stunnel.conf >/dev/null 2>&1"
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)
        return proc

    def _runRsync(self, dirname):
        cmd = ""
        cmd += "/usr/bin/rsync -a . rsync://127.0.0.1/main"
        subprocess.Popen(cmd, shell=True, universal_newlines=True).wait()


def _genSelfSignedCertAndKey(cn, keysize):
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, keysize)

    cert = crypto.X509()
    cert.get_subject().CN = cn
    cert.set_serial_number(random.randint(0, 65535))
    cert.gmtime_adj_notBefore(100 * 365 * 24 * 60 * 60 * -1)
    cert.gmtime_adj_notAfter(100 * 365 * 24 * 60 * 60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha1')

    return (cert, k)

