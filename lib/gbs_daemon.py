#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class GbsDaemon:

    def __init__(self, param):
        self.param = param
        self.soupServer = None
        self.sysDict = dict()
        self.mainloop = None

    def run(self):
        FrsUtil.mkDirAndClear(self.param.tmpDir)
        try:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
            logging.getLogger().setLevel(GbsUtil.getLoggingLevel(self.param.logLevel))
            logging.info("Program begins.")

            # create main loop
            self.mainloop = GLib.MainLoop()

            # write pid file
            with open(self.param.pidFile, "w") as f:
                f.write(str(os.getpid()))

            # start soup server
            self.soupServer = Soup.Server()
            self.soupServer.add_handler(None, self._httpRequestHandler)
            self.soupServer.listen_all(self.param.port, 0)
            logging.info('RESTful web service started.')

            # start main loop
            logging.info("Mainloop begins.")
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, self._sigHandlerINT, None)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, self._sigHandlerTERM, None)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGUSR2, self._sigHandlerUSR2, None)    # let the process ignore SIGUSR2, we
            signal.siginterrupt(signal.SIGUSR2, True)                                               # use it to interrupt blocking system calls
            self.mainloop.run()
            logging.info("Mainloop exits.")
        finally:
            if self.soupServer is not None:
                self.serverSock.disconnect()
            for obj in self.sysDict.values():
                self.closeSys(obj)
            logging.shutdown()
            shutil.rmtree(self.param.runDir)
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

    def _httpRequestHandler(self, server, msg, path, query, client):
        # all the request must NOT be processed parallelized
        assert server == self.soupServer
        try:
            if path == "/":
                pathList = []
            else:
                pathList = path.split("/")[1:]
            if len(pathList) != 2:
                raise GbsBusinessException(500)                     # fixme

            if msg.get_property("method") == "GET":
                ret = self.doGet(pathList[0], pathList[1])
                msg.set_status_code(200)
                msg.set_reponse("text/json", ret, len(ret))
            elif msg.get_property("method") == "PUT":
                self.doPut(self, pathList[0], pathList[1])
                msg.set_status_code(200)
            elif msg.get_property("method") == "DELETE":
                self.doDelete(self, pathList[0], pathList[1])
                msg.set_status_code(200)
            else:
                msg.set_status_code_full(e.status_code)
                # headers = SoupMessageHeaders(SOUP_MESSAGE_HEADERS_RESPONSE)
                # headers.append("Allow", )
        except GbsBusinessException as e:
            if e.reason_phrase is None:
                msg.set_status_code(e.status_code, e.reason_phrase)
            else:
                msg.set_status_code_full(e.status_code)

    def doGet(self, userName, systemName):
        """
        out-obj {
            "active": bool,           # if this system is running
            "dumpe2fs": str,          # dumpe2fs for the system disk image file
            "rsync-port": int,        # 
            "ssh-port": int,          # 
            "ftp-port": int,          # optional
            "ssh-public-key": str,    # 
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)

        obj = self.sysDict.get((userName, systemName))
        ret = {
            "active": (obj is not None),
            "dumpe2fs": GbsCommon.systemDumpDiskInfo(self.param, userName, systemName),
        }
        if obj is not None:
            if obj.rsyncPort is not None:
                ret["rsync-port"] = obj.rsyncPort
            if obj.sshPort is not None:
                ret["ssh-port"] = obj.sshPort
            if obj.ftpPort is not None:
                ret["ftp-port"] = obj.ftpPort
            if obj.sshPubKey is not None:
                ret["ssh-public-key"] = obj.sshPubKey
        return json.dumps(ret)

    def doPut(self, userName, systemName, clientArgs):
        """
        in-obj {
            "state": str,      # enum: "idle", "emerge+sync", "emerge+binpkg", "fpemud-refsystem-update"
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            GbsCommon.addSystem(userName, systemName)

        mode = clientArgs.get("state")
        if mode is not None:
            if mode == "idle":
                obj = self.sysDict.get((userName, systemName))
                if obj is not None:
                    self.closeSysObj(obj)
                    del self.sysDict[(userName, systemName)]
                else:
                    pass
            else:
                if (userName, systemName) not in self.sysDict:
                    obj = GbsSystem()
                    self.openSysObj(obj)
                    self.sysDict[(userName, systemName)] = obj
                else:
                    raise GbsBusinessException(500)                     # fixme
                     
    def doDelete(self, userName, systemName):
        if (userName, systemName) in self.sysDict:
            raise GbsBusinessException(500)                     # fixme
        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)
        GbsCommon.removeSystem(userName, systemName)

    def openSysObj(self, sysObj):
        sysObj.mntDir = os.path.join(self.tmpDir, userName, systemName)
        os.makedirs(sysObj.mntDir)





    def closeSysObj(self, sysObj):
        pass


class GbsBusinessException(Exception):
    def __init__(self, status_code, reason_phrase=None):
        self.statusCode = statusCode
        self.reason_phrase = reason_phrase


class GbsPluginModeException(Exception):
    pass


class GbsSystem:

    def __init__(self):
        self.mntDir = None
        self.rsyncPort = None
        self.sshPort = None
        self.ftpPort = None
        self.sshPubKey = None