#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import sys
import pwd
import grp
import dbus
import time
import random
import logging
import shutil
import subprocess
import socket
from OpenSSL import crypto
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop


class GbsUtil:

    @staticmethod
    def forceUnmount(mntDir):
        for i in range(0, 10):
            rc, out = GbsUtil.shell("/bin/umount %s" % (mntDir), "retcode+stdout")
            if rc == 0:
                return
            time.sleep(1.0)
        GbsUtil.shell("/bin/umount %s" % (mntDir))

    @staticmethod
    def mergeDictWithOverwriteAsException(dict1, dict2):
        for k in dict2.keys():
            if k in dict1:
                raise Exception("overwriting occured when merging two dictionaries")
        dict1.update(dict2)

    @staticmethod
    def isUserNameValid(userName):
        # from is_valid_name() in shadow-utils-4.1
        return re.search("^[a-z_][a-z0-9_-]*$", userName) is not None

    @staticmethod
    def isHostnameValid(hostname):
        # from RFC1123
        return re.search("^[a-z0-9][a-z0-9-]*$", hostname) is not None

    @staticmethod
    def dropPrivileges(uid_name, gid_name):
        os.setgid(grp.getgrnam(gid_name)[2])
        os.setuid(pwd.getpwnam(uid_name)[2])
        # os.umask(077)

    @staticmethod
    def chown(filename, uid_name, gid_name):
        os.chown(filename, pwd.getpwnam(uid_name)[2], grp.getgrnam(gid_name)[2])

    @staticmethod
    def idleInvoke(func, *args):
        def _idleCallback(func, *args):
            func(*args)
            return False
        GLib.idle_add(_idleCallback, func, *args)

    @staticmethod
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

    @staticmethod
    def waitTcpPort(port):
        # bad design, would cause an extra connection for server, may send SYN, wait ACK, but not send SYN-ACK
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(('127.0.0.1', port))
                s.close()
                break
            except socket.error:
                s.close()
                time.sleep(1.0)

    @staticmethod
    def copyToDir(srcFilename, dstdir, mode=None):
        """Copy file to specified directory, and set file mode if required"""

        if not os.path.isdir(dstdir):
            os.makedirs(dstdir)
        fdst = os.path.join(dstdir, os.path.basename(srcFilename))
        shutil.copy(srcFilename, fdst)
        if mode is not None:
            GbsUtil.shell("/bin/chmod " + mode + " \"" + fdst + "\"")

    @staticmethod
    def copyToFile(srcFilename, dstFilename, mode=None):
        """Copy file to specified filename, and set file mode if required"""

        if not os.path.isdir(os.path.dirname(dstFilename)):
            os.makedirs(os.path.dirname(dstFilename))
        shutil.copy(srcFilename, dstFilename)
        if mode is not None:
            GbsUtil.shell("/bin/chmod " + mode + " \"" + dstFilename + "\"")

    @staticmethod
    def getDirFreeSpace(dirname):
        """Returns free space in MB"""

        ret = GbsUtil.shell("/bin/df -BM \"%s\"" % (dirname), "stdout").decode("ascii")
        m = re.search("^.* + [0-9]+M +[0-9]+M +([0-9]+)M +[0-9]+% .*$", ret, re.M)
        return int(m.group(1))

    @staticmethod
    def getLoopDevByFile(filename):
        ret = GbsUtil.shell("/sbin/losetup -j \"%s\"" % (filename), "stdout").decode("ascii")
        m = re.search("^(.*?):.*$", ret, re.M)
        return m.group(1)

    @staticmethod
    def mkDir(dirname):
        if not os.path.isdir(dirname):
            GbsUtil.forceDelete(dirname)
            os.mkdir(dirname)

    @staticmethod
    def mkDirAndClear(dirname):
        GbsUtil.forceDelete(dirname)
        os.mkdir(dirname)

    @staticmethod
    def touchFile(filename):
        assert not os.path.exists(filename)
        f = open(filename, 'w')
        f.close()

    @staticmethod
    def forceDelete(filename):
        if os.path.islink(filename):
            os.remove(filename)
        elif os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isdir(filename):
            shutil.rmtree(filename)

    @staticmethod
    def ensureDir(dirname):
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    @staticmethod
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

    @staticmethod
    def shellInteractive(cmd, strInput, flags=""):
        """Execute shell command with input interaction"""

        assert cmd.startswith("/")

        # Execute shell command, throws exception when failed
        if flags == "":
            proc = subprocess.Popen(cmd,
                                    shell=True,
                                    stdin=subprocess.PIPE)
            proc.communicate(strInput)
            if proc.returncode != 0:
                raise Exception("Executing shell command \"%s\" failed, return code %d" % (cmd, proc.returncode))
            return

        # Execute shell command, throws exception when failed, returns stdout+stderr
        if flags == "stdout":
            proc = subprocess.Popen(cmd,
                                    shell=True,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            out = proc.communicate(strInput)[0]
            if proc.returncode != 0:
                raise Exception("Executing shell command \"%s\" failed, return code %d, output %s" % (cmd, proc.returncode, out))
            return out

        # Execute shell command, returns (returncode,stdout+stderr)
        if flags == "retcode+stdout":
            proc = subprocess.Popen(cmd,
                                    shell=True,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            out = proc.communicate(strInput)[0]
            return (proc.returncode, out)

        assert False

    @staticmethod
    def cbConditionToStr(cb_condition):
        ret = ""
        if cb_condition & GLib.IO_IN:
            ret += "IN "
        if cb_condition & GLib.IO_OUT:
            ret += "OUT "
        if cb_condition & GLib.IO_PRI:
            ret += "PRI "
        if cb_condition & GLib.IO_ERR:
            ret += "ERR "
        if cb_condition & GLib.IO_HUP:
            ret += "HUP "
        if cb_condition & GLib.IO_NVAL:
            ret += "NVAL "
        return ret

    @staticmethod
    def getLoggingLevel(logLevel):
        if logLevel == "CRITICAL":
            return logging.CRITICAL
        elif logLevel == "ERROR":
            return logging.ERROR
        elif logLevel == "WARNING":
            return logging.WARNING
        elif logLevel == "INFO":
            return logging.INFO
        elif logLevel == "DEBUG":
            return logging.DEBUG
        else:
            assert False

    @staticmethod
    def execHelper(*kargs):
        assert len(kargs) > 1

        cmd = ""
        cmd += "/usr/libexec/syncupd-helper exec"
        for arg in kargs:
            cmd += " \"%s\"" % (arg)

        proc = subprocess.Popen(cmd,
                                shell=True, universal_newlines=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        out, err = proc.communicate()
        if proc.returncode != 0:
            raise Exception(err)

        return out

    @staticmethod
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

    @staticmethod
    def dumpCertAndKey(cert, key, certFile, keyFile):
        with open(certFile, "wb") as f:
            buf = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
            f.write(buf)
            os.fchmod(f.fileno(), 0o644)

        with open(keyFile, "wb") as f:
            buf = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)
            f.write(buf)
            os.fchmod(f.fileno(), 0o600)

    @staticmethod
    def getQemuCpuModel(cpuArch, cpuModel):
        """$(uname -p) -> cpuModel"""

        # return cpu model of the lowest level
        if cpuModel is None:
            if cpuArch == "amd64":
                return "core2duo"
            elif cpuArch == "x86":
                return "pentium"
            else:
                assert False

        if cpuModel.startswith("Intel(R) Core(TM) i7-4600U CPU"):
            return "Haswell"
        else:
            assert False


class AvahiServiceRegister:

    """
    Exampe:
        obj = AvahiServiceRegister()
        obj.add_service(socket.gethostname(), "_http", 80)
        obj.start()
        obj.stop()
    """

    def __init__(self):
        self.retryInterval = 30
        self.serviceList = []

    def add_service(self, service_name, service_type, port):
        assert isinstance(service_name, str)
        assert service_type.endswith("._tcp") or service_type.endswith("._udp")
        assert isinstance(port, int)
        self.serviceList.append((service_name, service_type, port))

    def start(self):
        DBusGMainLoop(set_as_default=True)

        self._server = None
        self._retryCreateServerTimer = None
        self._entryGroup = None
        self._retryRegisterServiceTimer = None

        if dbus.SystemBus().name_has_owner("org.freedesktop.Avahi"):
            self._createServer()
        self._ownerChangeHandler = dbus.SystemBus().add_signal_receiver(self.onNameOwnerChanged, "NameOwnerChanged", None, None)

    def stop(self):
        if self._ownerChangeHandler is not None:
            dbus.SystemBus().remove_signal_receiver(self._ownerChangeHandler)
            self._ownerChangeHandler = None
        self._unregisterService()
        self._releaseServer()

    def onNameOwnerChanged(self, name, old, new):
        if name == "org.freedesktop.Avahi":
            if new != "" and old == "":
                if self._server is None:
                    self._createServer()
                else:
                    # this may happen on some rare case
                    pass
            elif new == "" and old != "":
                self._unregisterService()
                self._releaseServer()
            else:
                assert False

    def _createServer(self):
        assert self._server is None and self._retryCreateServerTimer is None
        assert self._entryGroup is None
        try:
            self._server = dbus.Interface(dbus.SystemBus().get_object("org.freedesktop.Avahi", "/"), "org.freedesktop.Avahi.Server")
            if self._server.GetState() == 2:    # avahi.SERVER_RUNNING
                self._registerService()
            self._server.connect_to_signal("StateChanged", self.onSeverStateChanged)
        except:
            logging.error("Avahi create server failed, retry in %d seconds" % (self.retryInterval), sys.exc_info())
            self._releaseServer()
            self._retryCreateServer()

    def _releaseServer(self):
        assert self._entryGroup is None
        if self._retryCreateServerTimer is not None:
            GLib.source_remove(self._retryCreateServerTimer)
            self._retryCreateServerTimer = None
        self._server = None

    def onSeverStateChanged(self, state, error):
        if state == 2:      # avahi.SERVER_RUNNING
            self._unregisterService()
            self._registerService()
        else:
            self._unregisterService()

    def _registerService(self):
        assert self._entryGroup is None and self._retryRegisterServiceTimer is None
        try:
            self._entryGroup = dbus.Interface(dbus.SystemBus().get_object("org.freedesktop.Avahi", self._server.EntryGroupNew()),
                                              "org.freedesktop.Avahi.EntryGroup")
            for serviceName, serviceType, port in self.serviceList:
                self._entryGroup.AddService(-1,                 # interface = avahi.IF_UNSPEC
                                            0,                  # protocol = avahi.PROTO_UNSPEC
                                            dbus.UInt32(0),     # flags
                                            serviceName,        # name
                                            serviceType,        # type
                                            "",                 # domain
                                            "",                 # host
                                            dbus.UInt16(port),  # port
                                            "")                 # txt
            self._entryGroup.Commit()
            self._entryGroup.connect_to_signal("StateChanged", self.onEntryGroupStateChanged)
        except:
            logging.error("Avahi register service failed, retry in %d seconds" % (self.retryInterval), sys.exc_info())
            self._unregisterService()
            self._retryRegisterService()

    def _unregisterService(self):
        if self._retryRegisterServiceTimer is not None:
            GLib.source_remove(self._retryRegisterServiceTimer)
            self._retryRegisterServiceTimer = None
        if self._entryGroup is not None:
            try:
                if self._entryGroup.GetState() != 4:        # avahi.ENTRY_GROUP_FAILURE
                    self._entryGroup.Reset()
                    self._entryGroup.Free()
                    # .Free() has mem leaks?
                    self._entryGroup._obj._bus = None
                    self._entryGroup._obj = None
            except dbus.exceptions.DBusException:
                pass
            finally:
                self._entryGroup = None

    def onEntryGroupStateChanged(self, state, error):
        if state in [0, 1, 2]:  # avahi.ENTRY_GROUP_UNCOMMITED, avahi.ENTRY_GROUP_REGISTERING, avahi.ENTRY_GROUP_ESTABLISHED
            pass
        elif state == 3:        # avahi.ENTRY_GROUP_COLLISION
            self._unregisterService()
            self._retryRegisterService()
        elif state == 4:        # avahi.ENTRY_GROUP_FAILURE
            assert False
        else:
            assert False

    def _retryCreateServer(self):
        assert self._retryCreateServerTimer is None
        self._retryCreateServerTimer = GLib.timeout_add_seconds(self.retryInterval, self.__timeoutCreateServer)

    def __timeoutCreateServer(self):
        self._retryCreateServerTimer = None
        self._createServer()                    # no exception in self._createServer()
        return False

    def _retryRegisterService(self):
        assert self._retryRegisterServiceTimer is None
        self._retryRegisterServiceTimer = GLib.timeout_add_seconds(self.retryInterval, self.__timeoutRegisterService)

    def __timeoutRegisterService(self):
        self._retryRegisterServiceTimer = None
        self._registerService()                 # no exception in self._registerService()
        return False
