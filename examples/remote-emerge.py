#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import json
import time
import socket
import random
import subprocess
from OpenSSL import crypto
from OpenSSL import SSL


def genSelfSignedCertAndKey(cn, keysize):
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

def dumpCertAndKey(cert, key, certFile, keyFile):
    with open(certFile, "wb") as f:
        buf = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        f.write(buf)
        os.fchmod(f.fileno(), 0o644)

    with open(keyFile, "wb") as f:
        buf = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
        f.write(buf)
        os.fchmod(f.fileno(), 0o600)


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


def getFreeTcpPort(start_port=10000, end_port=65536):
    for port in range(start_port, end_port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((('', port)))
            return port
        except socket.error:
            continue
        finally:
            s.close()
    raise Exception("No valid tcp port in [%d,%d]." % (start_port, end_port))


def waitTcpPort(port):
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', port))
            s.close()
            break
        except socket.error:
            s.close()
            time.sleep(1.0)


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


def createStunnelProcess(hostname, port):
    newPort = getFreeTcpPort()
    try:
        buf = ""
        buf += "cert = ./cert.pem\n"
        buf += "key = ./privkey.pem\n"
        buf += "\n"
        buf += "client = yes\n"
        buf += "foreground = yes\n"
        buf += "\n"
        buf += "[rsync]\n"
        buf += "accept = %d\n" % (newPort)
        buf += "connect = %s:%d\n" % (hostname, port)
        with open("./stunnel.conf", "w") as f:
            f.write(buf)

        proc = subprocess.Popen("/usr/sbin/stunnel ./stunnel.conf 2>/dev/null", shell=True, universal_newlines=True)
        waitTcpPort(newPort)

        return ("./stunnel.conf", newPort, proc)
    except:
        os.unlink("./stunnel.conf")
        raise


def syncUp(ip, port):
    stunnelCfgFile, newPort, proc = createStunnelProcess(ip, port)
    try:
        cmd = ""
        cmd += "/usr/bin/rsync -a -z -hhh --delete --delete-excluded --partial --info=progress2 "
        cmd += "-f '+ /bin' "             # /bin may be a symlink or directory
        cmd += "-f '+ /bin/***' "
        cmd += "-f '+ /boot/***' "
        cmd += "-f '- /etc/resolv.conf' "
        cmd += "-f '+ /etc/***' "
        cmd += "-f '+ /lib' "             # /lib may be a symlink or directory
        cmd += "-f '+ /lib/***' "
        cmd += "-f '+ /lib32' "           # /lib32 may be a symlink or directory
        cmd += "-f '+ /lib32/***' "
        cmd += "-f '+ /lib64' "           # /lib64 may be a symlink or directory
        cmd += "-f '+ /lib64/***' "
        cmd += "-f '+ /opt/***' "
        cmd += "-f '+ /sbin' "            # /sbin may be a symlink or directory
        cmd += "-f '+ /sbin/***' "
        cmd += "-f '+ /usr/***' "
        cmd += "-f '+ /var' "
        cmd += "-f '+ /var/portage/***' "
        cmd += "-f '+ /var/cache' "
        cmd += "-f '+ /var/cache/edb/***' "
        cmd += "-f '+ /var/db' "
        cmd += "-f '+ /var/db/pkg/***' "
        cmd += "-f '+ /var/lib' "
        cmd += "-f '+ /var/lib/portage/***' "
        cmd += "-f '- /**' "
        cmd += "/ rsync://127.0.0.1:%d/main" % (newPort)
        shell(cmd)
    finally:
        proc.terminate()
        proc.wait()
        os.unlink(stunnelCfgFile)


def sshExec(ip, port, key, argList):
    with open("./ssh_identity", "w") as f:
        f.write(key)
    os.chmod("./ssh_identity", 0o600)

    buf = ""
    buf += "KbdInteractiveAuthentication no\n"
    buf += "PasswordAuthentication no\n"
    buf += "PubkeyAuthentication yes\n"
    buf += "PreferredAuthentications publickey\n"
    buf += "\n"
    buf += "IdentityFile ./ssh_identity\n"
    buf += "UserKnownHostsFile /dev/null\n"
    buf += "StrictHostKeyChecking no\n"
    buf += "\n"
    with open("./ssh_config", "w") as f:
        f.write(buf)

    cmd = ""
    cmd += "/usr/bin/ssh -t -p %d -F ./ssh_config %s emerge %s" % (port, ip, " ".join(argList))
    shell(cmd)


def syncDown(ip, port):
    stunnelCfgFile, newPort, proc = self._createStunnelProcess(ip, port)
    try:
        cmd = ""
        cmd += "/usr/bin/rsync -a -z -hhh --delete --info=progress2 "
        cmd += "-f '+ /bin' "             # /bin may be a symlink or directory
        cmd += "-f '+ /bin/***' "
        cmd += "-f '- /etc/resolv.conf' "
        cmd += "-f '+ /etc/***' "
        cmd += "-f '+ /lib' "             # /lib may be a symlink or directory
        cmd += "-f '+ /lib/***' "
        cmd += "-f '+ /lib32' "           # /lib may be a symlink or directory
        cmd += "-f '+ /lib32/***' "
        cmd += "-f '+ /lib64' "           # /lib may be a symlink or directory
        cmd += "-f '+ /lib64/***' "
        cmd += "-f '+ /opt/***' "
        cmd += "-f '+ /sbin' "            # /sbin may be a symlink or directory
        cmd += "-f '+ /sbin/***' "
        cmd += "-f '+ /usr/***' "
        cmd += "-f '+ /var' "
        cmd += "-f '+ /var/portage/***' "
        cmd += "-f '+ /var/cache' "
        cmd += "-f '+ /var/cache/edb/***' "
        cmd += "-f '+ /var/db' "
        cmd += "-f '+ /var/db/pkg/***' "
        cmd += "-f '+ /var/lib' "
        cmd += "-f '+ /var/lib/portage/***' "
        cmd += "-f '- /**' "
        cmd += "rsync://127.0.0.1:%d/main /" % (newPort)
        FmUtil.shell(cmd)
    finally:
        proc.terminate()
        proc.wait()
        os.unlink(stunnelCfgFile)


if __name__ == "__main__":
    dstHostname = ""
    dstPort = 2108

    if os.getuid() != 0:
        print("priviledge error")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("argument error")
        sys.exit(1)
    dstHostname = sys.argv[1]

    print(">> Init.")

    if not os.path.exists("./cert.pem") or not os.path.exists("./privkey.pem"):
        cert, key = genSelfSignedCertAndKey("syncupd-example", 1024)
        dumpCertAndKey(cert, key, "./cert.pem", "./privkey.pem")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((dstHostname, dstPort))

    ctx = SSL.Context(SSL.SSLv3_METHOD)
    ctx.use_certificate_file("./cert.pem")
    ctx.use_privatekey_file("./privkey.pem")
    sslSock = SSL.Connection(ctx, sock)
    sslSock.set_connect_state()

    req = dict()
    req["command"] = "init"
    req["hostname"] = socket.gethostname()
    req["cpu-arch"] = getArch()
    req["plugin"] = "gentoo"
    sendRequestObj(sslSock, req)
    resp = recvReponseObj(sslSock)

    print(">> Sync up.")

    req = dict()
    req["command"] = "stage"
    sendRequestObj(sslSock, req)
    resp = recvReponseObj(sslSock)
    if "error" in resp:
        print(str(resp))
        sys.exit(1)
    assert resp["return"]["stage"] == 1

    syncUp(dstHostname, resp["return"]["rsync-port"])

    print(">> Emerging.")

    req = dict()
    req["command"] = "stage"
    sendRequestObj(sslSock, req)
    resp = recvReponseObj(sslSock)
    if "error" in resp:
        print(str(resp))
        sys.exit(1)
    assert resp["return"]["stage"] == 2

    sshExec(dstHostname, resp["return"]["ssh-port"], resp["return"]["ssh-key"], sys.argv[2:])

    print(">> Sync down.")

    req = dict()
    req["command"] = "stage"
    sendRequestObj(sslSock, req)
    resp = recvReponseObj(sslSock)
    if "error" in resp:
        print(str(resp))
        sys.exit(1)
    assert resp["return"]["stage"] == 3

    syncDown(dstHostname, resp["return"]["rsync-port"])
