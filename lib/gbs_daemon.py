#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import dbus
import time
import shutil
import subprocess
import netifaces
import socket
from gbs_util import GbsUtil
from gbs_common import GbsCommon


class GbsDaemon:

    def __init__(self, param):
        self.param = param

    def run(self):
        try:
            dbusObj = dbus.SystemBus().get_object('org.fpemud.CGFW', '/org/fpemud/CGFW')
            self.cgfwInterface = dbusObj.GetInterface()
            self.cgfwPrefixList = dbusObj.GetPrefixList()
            self.cgfwEnabled = True
        except:
            self.cgfwPrefixList = []
            self.cgfwInterface = None
            self.cgfwEnabled = False

        vpnProcList = []
        dnsmasqProc = None

        FcsUtil.mkDirAndClear(self.param.tmpDir)
        try:
            os.mkdir(os.path.join(self.param.tmpDir, "hosts.d"))
            for i in range(0, len(self.flist)):
                info = FcsCommon.entryGetInfo(self.flist[i])
                if info[1] == "openvpn":
                    proc = self._runOpenvpnServer(i)
                elif info[1] == "ipsec":                                                # fixme: unusable currently
                    proc = self._runIpsecServer(i)
                elif info[1] == "pptp":                                                 # fixme: unusable currently, and pptp is insecure, pppd sucks since it does not support multi-instance
                    proc = self._runPptpServer(i)
                else:
                    assert False
                vpnProcList.append(proc)
                FcsCommon.addNftNatRule("10.8.%d.0" % (i), "255.255.255.0", self.oif)

            # open ipv4 forwarding, currently no other program needs it, so we do a simple implementation
            with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
                f.write("1")

            self._waitOpenvpnInterfaces()
            dnsmasqProc = self._runDnsmasq()

            FcsUtil.suspend()
        finally:
            if dnsmasqProc is not None:
                dnsmasqProc.terminate()
                dnsmasqProc.wait()

            with open("/proc/sys/net/ipv4/ip_forward", "w") as f:
                f.write("0")

            for i in range(0, len(vpnProcList)):
                FcsCommon.removeNftNatRule("10.8.%d.0" % (i), "255.255.255.0")
                vpnProcList[i].terminate()
                vpnProcList[i].wait()

            shutil.rmtree(self.param.tmpDir)

    def _cleanupHosts(self):
        lineList = []
        lineList2 = []
        with open("/etc/hosts", "r") as f:
            b = -1
            for line in f.read().rstrip("\n").split("\n"):
                if line == "### fpemud-vpn-server begin ###":
                    b = 0
                if b == -1:
                    lineList.append(line)
                if b == 1:
                    lineList2.append(line)
                if line == "### fpemud-vpn-server end ###":
                    b = 1

        if lineList2 == []:
            return

        with open("/etc/hosts", "w") as f:
            f.write("\n".join(lineList + lineList2))
            f.write("\n")

    def _runOpenvpnServer(self, i):
        info = FcsCommon.entryGetInfo(self.flist[i])
        cfgf = os.path.join(self.param.tmpDir, "openvpn-%d.conf" % (i))
        gwIf = FcsUtil.getGatewayInterface()

        # generate openvpn config file
        # notes:
        # 1. no comp-lzo. it seems that "push comp-lzo" leads to errors, and I don't think compression saves much
        with open(cfgf, "w") as f:
            f.write("tmp-dir %s\n" % (self.param.tmpDir))

            f.write("proto %s\n" % (info[2]))
            f.write("port %s\n" % (info[3]))
            f.write("\n")

            f.write("dev-type tun\n")
            f.write("dev vpns%d\n" % (i))
            f.write("keepalive 10 120\n")
            f.write("\n")

            f.write("local %s\n" % (FcsUtil.getInterfaceIp(gwIf)))
            f.write("server 10.8.%d.0 255.255.255.0\n" % (i))
            f.write("topology subnet\n")
            f.write("client-to-client\n")
            f.write("\n")

            f.write("duplicate-cn\n")
            # f.write("ns-cert-type client\n")
            f.write("verify-x509-name %s name\n" % (self.param.clientCertCn))
            f.write("\n")

            f.write("script-security 2\n")
            f.write("auth-user-pass-verify \"%s/openvpn-script-auth.sh\" via-env\n" % (self.param.libexecDir))
            f.write("client-connect \"%s/openvpn-script-client.py %s\"\n" % (self.param.libexecDir, self.param.tmpDir))
            f.write("client-disconnect \"%s/openvpn-script-client.py %s\"\n" % (self.param.libexecDir, self.param.tmpDir))
            f.write("\n")

            hasRoute = False
            for i2 in range(0, len(self.flist)):     # multiple VPN can communicate with each other
                if i2 != i:
                    f.write("push \"route 10.8.%d.0 255.255.255.0\"\n" % (i2))
                    hasRoute = True
            if info[4]:
                f.write("push \"redirect-gateway\"\n")
                hasRoute = True
            for ip, mask in self.cgfwPrefixList:
                f.write("push \"route %s %s\"\n" % (ip, mask))
                hasRoute = True
            if hasRoute:
                f.write("\n")

            f.write("push \"dhcp-option DNS 10.8.%d.1\"\n" % (i))
            f.write("\n")

            f.write("ca %s\n" % (self.param.caCertFile))
            f.write("cert %s\n" % (self.param.servCertFile))
            f.write("key %s\n" % (self.param.servKeyFile))
            f.write("dh %s\n" % (self.param.servDhFile))
            f.write("\n")

            # f.write("user nobody\n")
            # f.write("group nobody\n")
            # f.write("\n")

            f.write("persist-key\n")
            f.write("persist-tun\n")
            f.write("\n")

            f.write("status %s/openvpn-status-%d.log\n" % (self.param.tmpDir, i))
            f.write("status-version 2\n")
            f.write("verb 4\n")

        # run openvpn process
        cmd = ""
        cmd += "/usr/sbin/openvpn "
        cmd += "--config %s " % (cfgf)
        cmd += "--writepid %s/openvpn-%d.pid " % (self.param.tmpDir, i)
        cmd += "> %s/openvpn-%d.out 2>&1" % (self.param.tmpDir, i)
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

        return proc

    def _runIpsecServer(self, i):
        info = FcsCommon.entryGetInfo(self.flist[i])
        cfgf = os.path.join(self.param.tmpDir, "ipsec-%d.conf" % (i))
        secretf = os.path.join(self.param.tmpDir, "ipsec-%d.secret" % (i))
        gwIf = FcsUtil.getGatewayInterface()

        # generate ipsec.conf
        buf = ""
        buf += "config setup\n"
        buf += "    protostack=netkey\n"
        buf += "    logfile=%s/pluto-%d.log\n" % (self.param.tmpDir, i)
        buf += "    dumpdir=%s/pluto-%d\n" % (self.param.tmpDir, i)
        buf += "    virtual_private=%v4:10.0.0.0/8,%v4:192.168.0.0/16,%v4:172.16.0.0/12,%v4:25.0.0.0/8,%v4:100.64.0.0/10,%v6:fd00::/8,%v6:fe80::/10\n"
        buf += "\n"
        buf += "conn iPhone\n"
        buf += "    authby=secret|rsasig\n"
#        buf += "    pfs=no\n"
#        buf += "    rekey=no\n"
#        buf += "    keyingtries=3\n"
        buf += "    left=%defaultroute\n"
        buf += "    leftprotoport=udp/%any\n"
        buf += "    right=%any\n"
        buf += "    rightprotoport=udp/%any\n"
#        buf += "    auto=add\n"
#        buf += "    ike=aes128-sha1\n"
#        buf += "    esp=aes128-sha1,aes256-sha1\n"
        buf += "    forceencaps=yes\n"
        with open(cfgf, "w") as f:
            f.write(buf)

        # generate ipsec.secret
        buf = ""
        buf += ": RSA %s\n" % (self.param.servKeyFile)
        if info[2] is not None:
            buf += "%s %any: PSK \"%s\"\n" % (FcsUtil.getInterfaceIp(gwIf), info[2])
            buf += "@fpemud-vpn : XAUTH \"%s\"\n" % (info[2])
        with open(secretf, "w") as f:
            f.write(buf)
        os.chmod(secretf, 0o600)

        # run pluto process
        cmd = "/usr/libexec/ipsec/pluto "
        cmd += "--config %s " % (cfgf)
        cmd += "--secretsfile %s " % (secretf)
        cmd += "--ctlbase %s/pluto-%d " % (self.param.tmpDir, i)
        cmd += "--interface %s " % (gwIf)
        cmd += "--nofork "
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

        return proc

    def _runPptpServer(self, i):
        info = FcsCommon.entryGetInfo(self.flist[i])
        cfgf = os.path.join(self.param.tmpDir, "pptpd-%d.conf" % (i))
        secretf = os.path.join(self.param.tmpDir, "pptpd-%d.secret" % (i))
        gwIf = FcsUtil.getGatewayInterface()

        if not os.path.exists("/etc/ppp/options.pptpd"):
            raise Exception("/etc/ppp/options.pptpd does not exist")

        # generate pptpd.conf
        buf = ""
        buf += "option /etc/ppp/options.pptpd\n"
        buf += "localip 10.8.%d.1\n" % (i)
        buf += "remoteip 10.8.%d.2-254\n" % (i)
        with open(cfgf, "w") as f:
            f.write(buf)

        # generate secret file
        buf = ""
        buf += "# <username> <server name> <password> <ip addresses>\n"
        buf += "%s pptpd %s *\n" % (info[2], info[3])
        with open(secretf, "w") as f:
            f.write(buf)

        # run pptpd process
        cmd = "/usr/bin/pptpd "
        cmd += "--conf %s " % (cfgf)
        cmd += "--pidfile %s/pptpd-%d.pid " % (self.param.tmpDir, i)
        cmd += "--listen %s " % (FcsUtil.getInterfaceIp(gwIf))
        cmd += "--fg "
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

        return proc

    def _waitOpenvpnInterfaces(self):
        ifnameSet = set()
        for i in range(0, len(self.flist)):
            info = FcsCommon.entryGetInfo(self.flist[i])
            if info[1] == "openvpn":
                ifnameSet.add("vpns%d" % (i))

        while True:
            ret = ifnameSet - set(netifaces.interfaces())
            if len(ret) == 0:
                break
            time.sleep(1.0)

    def _runDnscrypt(self, port):
        # run dnscrypt-proxy process
        cmd = ""
        cmd += "/usr/sbin/dnscrypt-proxy "
        cmd += "--pidfile=%s/dnscrypt-proxy.pid " % (self.param.tmpDir)
        cmd += "--logfile=%s/dnscrypt-proxy.log " % (self.param.tmpDir)
        cmd += "--user=dnscrypt "
        cmd += "--local-address=127.0.0.1:%d " % (port)
        cmd += "--resolver-address=208.67.220.220:443 "             # --fixme
        cmd += "--provider-name=2.dnscrypt-cert.opendns.com "       # --fixme
        cmd += "--provider-key=B735:1140:206F:225D:3E2B:D822:D7FD:691E:A1C3:3CC8:D666:8D0C:BE04:BFAB:CA43:FB79 "  # --fixme
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

        return proc

    def _runDnsmasq(self):
        # generate dnsmasq config file
        buf = ""
        buf += "strict-order\n"
        buf += "bind-interfaces\n"                            # don't listen on 0.0.0.0
        buf += "interface=vpns*\n"
        buf += "except-interface=lo\n"                        # don't listen on 127.0.0.1
        buf += "user=root\n"
        buf += "group=root\n"
        buf += "domain-needed\n"
        buf += "bogus-priv\n"
        buf += "no-hosts\n"
        buf += "hostsdir=%s\n" % (os.path.join(self.param.tmpDir, "hosts.d"))
        cfgf = os.path.join(self.param.tmpDir, "dnsmasq.conf")
        with open(cfgf, "w") as f:
            f.write(buf)

        # generate default hosts file
        with open(os.path.join(self.param.tmpDir, "hosts.d", "hosts.myhostname"), "w") as f:
            f.write("10.8.0.1 %s" % (socket.gethostname()))

        # run dnsmasq process
        cmd = "/usr/sbin/dnsmasq"
        cmd += " --keep-in-foreground"
        cmd += " --conf-file=\"%s\"" % (cfgf)
        cmd += " --pid-file=%s/dnsmasq.pid" % (self.param.tmpDir)
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

        return proc
