#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import logging
import shutil
import subprocess
import pwd
import socket
import re
import threading
from gi.repository import GLib
from gi.repository import GObject
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.ioloop import IOLoop
from pyftpdlib.servers import FTPServer

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
            SnUtil.shell("/bin/chmod " + mode + " \"" + fdst + "\"")

    @staticmethod
    def copyToFile(srcFilename, dstFilename, mode=None):
        """Copy file to specified filename, and set file mode if required"""

        if not os.path.isdir(os.path.dirname(dstFilename)):
            os.makedirs(os.path.dirname(dstFilename))
        shutil.copy(srcFilename, dstFilename)
        if mode is not None:
            SnUtil.shell("/bin/chmod " + mode + " \"" + dstFilename + "\"")

    @staticmethod
    def mkDir(dirname):
        if not os.path.isdir(dirname):
            SnUtil.forceDelete(dirname)
            os.mkdir(dirname)

    @staticmethod
    def mkDirAndClear(dirname):
        SnUtil.forceDelete(dirname)
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


class FTPd(threading.Thread):
    """
    It is a modified version of the class FTPd in pyftpdlib's test code.
    Wraps the polling loop of pyftpdlib.FTPServer class into a thread.
    The instance returned can be used to start(), stop() and eventually re-start() the server.
    This server is for read-only access.
    """
    handler = FTPHandler
    shutdown_after = 10
    _lock = threading.Lock()
    _flag_started = threading.Event()
    _flag_stopped = threading.Event()

    def __init__(self, port, homedir, allow_ip):
        threading.Thread.__init__(self)
        self._timeout = None
        self._serving = False
        self._stopped = False

        authorizer = DummyAuthorizer()
        authorizer.add_anonymous(homedir)
        self.handler.authorizer = authorizer
        # lower buffer sizes = more "loops" while transfering data = less false positives
        self.handler.dtp_handler.ac_in_buffer_size = 4096
        self.handler.dtp_handler.ac_out_buffer_size = 4096
        self.server = FTPServer(("0.0.0.0", port), self.handler)

    @property
    def running(self):
        return self._serving

    def start(self, timeout=0.001):
        """
        Start serving until an explicit stop() request.
        Polls for shutdown every 'timeout' seconds.
        """
        if self._serving:
            raise RuntimeError("Server already started")
        if self._stopped:
            # ensure the server can be started again
            FTPd.__init__(self, self.server.socket.getsockname(), self.handler)
        self._timeout = timeout
        threading.Thread.start(self)
        self._flag_started.wait()

    def run(self):
        self._serving = True
        self._flag_started.set()
        started = time.time()
        try:
            while self._serving:
                with self._lock:
                    self.server.serve_forever(timeout=self._timeout,
                                              blocking=False)
                if (self.shutdown_after and
                        time.time() >= started + self.shutdown_after):
                    now = time.time()
                    if now <= now + self.shutdown_after:
                        print("shutting down test FTPd due to timeout")
                        self.server.close_all()
                        raise Exception("test FTPd shutdown due to timeout")
            self.server.close_all()
        finally:
            self._flag_stopped.set()

    def stop(self):
        """
        Stop serving (also disconnecting all currently connected
        clients) by telling the serve_forever() loop to stop and
        waits until it does.
        """
        if not self._serving:
            raise RuntimeError("Server not started yet")
        if not self._stopped:
            self._serving = False
            self._stopped = True
            self.join(timeout=3)
            if threading.active_count() > 1:
                warn("test FTP server thread is still running")
            self._flag_stopped.wait()