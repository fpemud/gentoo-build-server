#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import socket
import subprocess
from OpenSSL import SSL


def sendRequestObj(sslSock, requestObj):
    s = json.dumps(requestObj) + "\n"
    sslSock.send(s.encode("iso8859-1"))


def recvReponseObj(sslSock):
    buf = b""
    while True:
        buf += sslSock.recv(4096)
        i = buf.find(b"\n")
        if i >= 0:
            assert i == len(buf) - 1
            return json.loads(buf[:i].decode("iso8859-1"))


def getArch():
    ret = shell("/usr/bin/uname -m", "stdout").decode("utf-8")
    ret = ret.rstrip('\n')
    if ret == "x86_64":
        return "amd64"
    else:
        return ret


def shell(cmd, flags=""):
    """Execute shell command"""

    assert cmd.startswith("/")

    # Execute shell command, throws exception when failed
    if flags == "":
        retcode = subprocess.Popen(cmd, shell=True).wait()
        if retcode != 0:
            raise Exception("Executing shell command \"%s\" failed, return code %d" % (cmd, retcode))
        return

    # Execute shell command, throws exception when failed, returns stdout+stderr
    if flags == "stdout":
        proc = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        out = proc.communicate()[0]
        if proc.returncode != 0:
            raise Exception("Executing shell command \"%s\" failed, return code %d" % (cmd, proc.returncode))
        return out

    # Execute shell command, returns (returncode,stdout+stderr)
    if flags == "retcode+stdout":
        proc = subprocess.Popen(cmd,
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        out = proc.communicate()[0]
        return (proc.returncode, out)

    assert False


def syncUp(ip, port, certFile, keyFile):
    buf = ""
    buf += "cert = %s\n" % (certFile)
    buf += "key = %s\n" % (keyFile)
    buf += "\n"
    buf += "client = yes\n"
    buf += "foreground = yes\n"
    buf += "\n"
    buf += "[rsync]\n"
    buf += "accept = 127.0.0.1:874\n"
    buf += "connect = %s:%d\n" % (ip, port)
    with open("./stunnel.conf", "w") as f:
        f.write(buf)

    buf = ""
    buf += "/boot\n"
    buf += "/dev/*\n"
    buf += "/proc/*\n"
    buf += "/sys/*\n"
    buf += "/root/*\n"
    buf += "/home/*\n"
    buf += "/media\n"
    buf += "/mnt\n"
    buf += "/run/*\n"
    buf += "/var/*\n"
    buf += "/tmp/*\n"
    with open("./exclude.rsync", "w") as f:
        f.write(buf)

    cmd = ""
    cmd += "/usr/sbin/stunnel ./stunnel.conf >/dev/null 2>&1"
    proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

    cmd = ""
    cmd += "/usr/bin/rsync -a --exclude-from=./exclude.rsync / rsync://127.0.0.1/main"
    subprocess.Popen(cmd, shell=True, universal_newlines=True).wait()

    proc.terminate()
    proc.wait()

    os.unlink("./exclude.rsync")
    os.unlink("./stunnel.conf")


def sshExec(ip, port, certFile, keyFile, argList):
    cmd = ""
    cmd += "/usr/bin/ssh %s:%d emerge %s" % (ip, port, " ".join(argList))
    subprocess.Popen(cmd, shell=True, universal_newlines=True).wait()


def syncDown(ip, port, certFile, keyFile):
    buf = ""
    buf += "cert = %s\n" % (certFile)
    buf += "key = %s\n" % (keyFile)
    buf += "\n"
    buf += "client = yes\n"
    buf += "foreground = yes\n"
    buf += "\n"
    buf += "[rsync]\n"
    buf += "accept = 127.0.0.1:874\n"
    buf += "connect = %s:%d\n" % (ip, port)
    with open("./stunnel.conf", "w") as f:
        f.write(buf)

    buf = ""
    buf += "/boot\n"
    buf += "/dev/*\n"
    buf += "/proc/*\n"
    buf += "/sys/*\n"
    buf += "/root/*\n"
    buf += "/home/*\n"
    buf += "/media\n"
    buf += "/mnt\n"
    buf += "/run/*\n"
    buf += "/var/*\n"
    buf += "/tmp/*\n"
    with open("./exclude.rsync", "w") as f:
        f.write(buf)

    cmd = ""
    cmd += "/usr/sbin/stunnel ./stunnel.conf >/dev/null 2>&1"
    proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

    cmd = ""
    cmd += "/usr/bin/rsync -a --dry-run -v --exclude-from=./exclude.rsync rsync://127.0.0.1/main /"
    subprocess.Popen(cmd, shell=True, universal_newlines=True).wait()

    proc.terminate()
    proc.wait()

    os.unlink("./exclude.rsync")
    os.unlink("./stunnel.conf")


if __name__ == "__main__":
    dstIp = ""
    dstPort = 2108
    if len(sys.argv) < 2:
        print("argument error")
        sys.exit(1)
    dstIp = sys.argv[1]

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((dstIp, dstPort))

    ctx = SSL.Context(SSL.SSLv3_METHOD)
    ctx.use_certificate_file("./cert.pem")
    ctx.use_privatekey_file("./privkey.pem")
    sslSock = SSL.Connection(ctx, sock)
    sslSock.set_connect_state()

    print(">> Init.")

    req = dict()
    req["command"] = "init"
    req["cpu-arch"] = getArch()
    req["size"] = 10
    req["plugin"] = "gentoo"
    req["mode"] = "emerge+sync"
    sendRequestObj(sslSock, req)
    resp = recvReponseObj(sslSock)

    print(">> Sync up.")

    req = dict()
    req["command"] = "stage"
    sendRequestObj(sslSock, req)
    resp = recvReponseObj(sslSock)

    syncUp(dstIp, resp["return"]["rsync-port"], "./cert.pem", "./privkey.pem")

    print(">> Emerging.")

    req = dict()
    req["command"] = "stage"
    sendRequestObj(sslSock, req)
    resp = recvReponseObj(sslSock)

    sshExec(dstIp, resp["return"]["ssh-port"], "./cert.pem", "./privkey.pem", sys.argv[2:])

    print(">> Sync down.")

    req = dict()
    req["command"] = "stage"
    sendRequestObj(sslSock, req)
    resp = recvReponseObj(sslSock)

    syncDown(dstIp, resp["return"]["rsync-port"], "./cert.pem", "./privkey.pem")
