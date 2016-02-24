#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import logging
import shutil
import subprocess
import socket
import Pyro4
from gi.repository import GLib
# from pyftpdlib.authorizers import DummyAuthorizer
# from pyftpdlib.handlers import FTPHandler
# from pyftpdlib.servers import FTPServer


class GbsUtil:

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
    def getFreeTcpPorts(port_num, start_port=10000, end_port=65536):
        ret = []
        for port in range(start_port, end_port):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind((('', port)))
                ret.append(port)
                if len(ret) >= port_num:
                    return ret
            except socket.error:
                continue
            finally:
                s.close()
        raise Exception("Not enough valid tcp port in [%d,%d]." % (start_port, end_port))

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
    def forceSymlink(source, link_name):
        if os.path.exists(link_name):
            os.remove(link_name)
        os.symlink(source, link_name)

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


class PyroServer:

    def __init__(self, ipaddr, port):
        self.pyroDaemon = Pyro4.Daemon(ipaddr, port)

    def attach(self, mainloop):
        GLib.io_add_watch(self.pyroDaemon.sockets[0], GLib.IO_IN, self._handleEvent)

    def register(self, name, obj):
        self.pyroDaemon.register(obj, name)

    def unregister(self, name):
        """no unregister needed currently"""
        assert False

    def _handleEvent(self, socket, *args):
        self.pyroDaemon.events([socket])
        return True