#!/usr/bin/env python2
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import socket
from OpenSSL import crypto


class TestClient:

    def __init__(self):
        self.sock = None
        self.sslSock = None

    def connect(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", port))

        cert, key = _genSelfSignedCertAndKey("test-client", 1024)
        _dumpCertAndKey(cert, key, "./cert.pem", "./privkey.pem")

        ctx = SSL.Context(SSL.SSLv3_METHOD)
        ctx.set_verify(SSL.VERIFY_PEER, _sslVerifyDummy)
        ctx.use_privatekey_file(keyFile)
        ctx.use_certificate_file(certFile)
        self.sslSock = SSL.Connection(ctx, self.sock)
        self.sslSock.set_connect_state()

    def dispose(self):
        self.sock.close()
        os.unlink("./privkey.pem")
        os.unlink("./cert.pem")

    def cmdInit(self, cpuArch, size, plugin):
        requestObj = dict()
        requestObj["command"] = "init"
        requestObj["cpu-arch"] = cpuArch
        requestObj["size"] = size
        requestObj["plugin"] = plugin
        self.sslSock.send(json.dumps(requestObj))
        return _recvReponseObj(self.sslSock)

    def cmdStage(self):
        pass

    def cmdQuit(self):
        requestObj = dict()
        requestObj["command"] = "quit"
        self.sslSock.send(json.dumps(requestObj))
        return _recvReponseObj(self.sslSock)


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


def _dumpCertAndKey(cert, key, certFile, keyFile):
    with open(certFile, "wb") as f:
        buf = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        f.write(buf)
        os.fchmod(f.fileno(), 0o644)

    with open(keyFile, "wb") as f:
        buf = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
        f.write(buf)
        os.fchmod(f.fileno(), 0o600)


def _sslVerifyDummy(conn, cert, errnum, depth, ok):
    return ok


def _recvReponseObj(sslSock):
    buf = ""
    while True:
        buf += self.sslSock.recv(4096)
        i = buf.find("\n")
        if i >= 0:
            assert i == len(buf)
            return json.loads(buf[:i])