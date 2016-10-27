#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import signal
import shutil
import logging
from gi.repository import GLib
from gbs_util import GbsUtil
from gbs_ctrl_server import GbsCtrlServer


class GbsDaemon:

    def __init__(self, param):
        self.param = param
        self.ctrlServer = None
        self.mainloop = None

    def run(self):
        GbsUtil.mkDirAndClear(self.param.tmpDir)
        GbsUtil.mkDirAndClear(self.param.runDir)
        try:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
            logging.getLogger().setLevel(GbsUtil.getLoggingLevel(self.param.logLevel))
            logging.info("Program begins.")

            # create main loop
            self.mainloop = GLib.MainLoop()

            # write pid file
            with open(self.param.pidFile, "w") as f:
                f.write(str(os.getpid()))

            # check certificate and private key
            if not os.path.exists(self.param.certFile) or not os.path.exists(self.param.privkeyFile):
                raise GbsDaemonException("Certificate and private key not found")

            # start control server
            self.ctrlServer = GbsCtrlServer(self.param)
            self.ctrlServer.start()
            logging.info('Control server started.')

            # start main loop
            logging.info("Mainloop begins.")
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, self._sigHandlerINT, None)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, self._sigHandlerTERM, None)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGUSR2, self._sigHandlerUSR2, None)    # let the process ignore SIGUSR2, we
            signal.siginterrupt(signal.SIGUSR2, True)                                               # use it to interrupt blocking system calls
            self.mainloop.run()
            logging.info("Mainloop exits.")
        finally:
            if self.ctrlServer is not None:
                self.ctrlServer.stop()
            logging.shutdown()
            shutil.rmtree(self.param.runDir)
            shutil.rmtree(self.param.tmpDir)
            logging.info("Program exits.")

    def _sigHandlerINT(self, signum):
        logging.info("SIGINT received.")
        self.mainloop.quit()
        return True

    def _sigHandlerTERM(self, signum):
        logging.info("SIGTERM received.")
        self.mainloop.quit()
        return True

    def _sigHandlerUSR2(self, signum):
        return True


class GbsDaemonException(Exception):
    pass