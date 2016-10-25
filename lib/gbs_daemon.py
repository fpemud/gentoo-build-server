#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import signal
import shutil
import logging
from gi.repository import GLib
from services.rsyncd import RsyncService
from gbs_util import GbsUtil
from gbs_common import GbsCommon
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
            self.ctrlServer = GbsCtrlServer(self.param, self.onConnect, self.onDisconnect, self.onRequest)
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

    def onConnect(self, pubkey):
        sessObj = GbsSession()
        sessObj.pubkey = pubkey
        sessObj.uuid = GbsCommon.findOrCreateSystem(self.param, pubkey)
        sessObj.cpuArch = None
        sessObj.plugin = None
        sessObj.stage = None
        sessObj.quited = False
        logging.info('Client \"%s\" connected.' % (sessObj.uuid))
        return sessObj

    def onDisconnect(self, sessId, sessObj):
        sessObj.plugin.disconnectHandler()
        logging.info('Client \"%s\" disconnected.' % (sessObj.uuid))

    def onRequest(self, sessId, sessObj, requestObj):
        if sessObj.quited:
            return
        try:
            if "command" not in requestObj:
                raise GbsDaemonException("Missing \"command\" in request object")

            if requestObj["command"] == "init":
                return self._cmdInit(sessId, sessObj, requestObj)
            elif requestObj["command"] == "stage":
                return self._cmdStage(sessId, sessObj, requestObj)
            elif requestObj["command"] == "quit":
                return self._cmdQuit(sessId, sessObj, requestObj)
            else:
                raise GbsDaemonException("Unknown command")
        except GbsDaemonException as e:
            logging.error(e.message + " from client \"%s\"." % (sessObj.uuid))
            sessObj.plugin.disconnectHandler()
            self.ctrlServer.closeSession(sessId)

    def _cmdInit(self, sessId, sessObj, requestObj):
        if "cpu-arch" not in requestObj:
            raise GbsDaemonException("Missing \"cpu-arch\" in init command")
        sessObj.cpuArch = requestObj["cpu-arch"]

        if "size" not in requestObj:
            raise GbsDaemonException("Missing \"size\" in init command")
        if requestObj["size"] > self.param.maxImageSize:
            raise GbsDaemonException("Value of \"size\" is too large in init command")
        sessObj.size = requestObj["size"]
        GbsCommon.systemResizeDisk(self.param, sessObj.uuid, sessObj.size)

        if "plugin" not in requestObj:
            raise GbsDaemonException("Missing \"plugin\" in init command")
        pyfname = requestObj["plugin"].replace("-", "_")
        exec("import %s" % (pyfname))
        self.plugin = eval("%s.PluginObject(GbsPluginApi(self, sessObj))" % (pyfname))

        sessObj.stage = 0

        sessObj.plugin.initHandler(requestObj)

        return {"return": {}}

    def _cmdStage(self, sessId, sessObj, requestObj):
        sessObj.stage += 1

        if sessObj.stage == 1:
            sessObj.rsyncServ = RsyncService()
            sessObj.rsyncServ.start()
            return {"return": {"rsync-port": sessObj.rsyncServ.getPort()}}

        if sessObj.stage == 2:
            sessObj.rsyncServ.stop()
            del sessObj.rsyncServ
            return sessObj.plugin.stageHandler()

        if True:
            return sessObj.plugin.stageHandler()

    def _cmdQuit(self, sessId, sessObj, requestObj):
        sessObj.quited = True

        def _temp(self, sessId, sessObj):
            sessObj.plugin.disconnectHandler()
            self.ctrlServer.closeSession(sessId)
        GbsUtil.idleInvoke(_temp, self, sessId, sessObj)

        return {"return": {}}


class GbsSession:

    def __init__(self):
        self.pubkey = None
        self.uuid = None
        self.imageSize = None           #
        self.cpuArch = None             # cpu architecture
        self.plugin = None              # plugin object
        self.stage = None               # stage number
        self.quited = None


class GbsDaemonException(Exception):
    pass


class GbsProtocolException(Exception):
    pass


class GbsBusinessException(Exception):
    pass


class GbsPluginApi:

    ProtocolException = GbsProtocolException
    BusinessException = GbsBusinessException

    def __init__(self, parent):
        self.parent = parent
