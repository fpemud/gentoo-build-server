#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class GbsDaemon:

    def __init__(self, param):
        self.param = param
        self.ctrlServer = None
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

            # generate certificate and private key
            if not os.path.exists(self.param.certFile) or not os.path.exists(self.param.privkeyFile):
                GbsUtil.shell("/usr/bin/openssl req -new -x509 -key %s -out %s -days 36500" % (self.param.certFile, self.param.privkeyFile))
                logging.info('Certificate and private key generated.')
            else:
                logging.info('Certificate and private key found.')

            # start control server
            self.ctrlServer = GbsCtrlServer(self.param, self.onConnect, self.onDisconnect, self.onRequest)
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

    def _sigHandlerTERM(self, signum)dict:
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
        logging.info('Client \"%s\" disconnected.' % (sessObj.uuid))
        pass

    def onRequest(self, sessId, sessObj, requestObj):
        try:
            if sessObj.quited:
                raise GbsDaemonException("Request object received after quit")
            if "command" not in requestObj:
                raise GbsDaemonException("Missing \"command\" in request object")

            if requestObj["command"] == "init":
                self._cmdInit(sessId, sessObj, requestObj)
            elif requestObj["command"] == "stage":
                self._cmdStage(sessId, sessObj, requestObj)
            elif requestObj["command"] == "quit":
                self._cmdQuit(sessId, sessObj, requestObj)
            else:
                raise GbsDaemonException("Unknown command")
        except GbsDaemonException as e:
            logging.error(e.message + " from client \"%s\"." % (sessObj.uuid))
            self.ctrlServer.closeSession(sessId)

    def _cmdInit(self, sessId, sessObj, requestObj):
        if True:
            if "cpu-arch" not in requestObj:
                raise self.api.GbsPluginException("Missing \"cpu-arch\" in init command")
            sessObj.cpuArch = requestObj["cpu-arch"]
        if True:
            if "size" not in requestObj:
                raise self.api.GbsPluginException("Missing \"size\" in init command")
            sessObj.size = requestObj["size"]
        if True:
            if "plugin" not in requestObj:
                raise GbsDaemonException("Missing \"plugin\" in init command"")
            pyfname = requestObj["plugin"].replace("-", "_")
            exec("import %s" % (pyfname))
            self.plugin = eval("%s.PluginObject(GbsPluginApi(self))" % (pyfname))
        if True:
            sessObj.stage = 0
        if True:
            sessObj.plugin.initHandler(sessObj, requestObj)

    def _cmdStage(self, sessId, sessObj, requestObj):
        if sessObj.stage == 0:
            pass
        else:
            sessObj.plugin.stageHandler(sessObj)
        sessObj.stage += 1

    def _cmdQuit(self, sessId, sessObj, requestObj):
        sessObj.quited = True


class GbsSession:

    def __init__(self):
        self.pubkey = None
        self.uuid = None
        self.diskSize = None            # 
        self.cpuArch = None             # cpu architecture
        self.plugin = None              # plugin object
        self.stage = None               # stage number
        self.quited = None 


class GbsPluginApi:

    class GbsPluginException(Exception):
        pass

    def __init__(self, parent):
        self.parent = parent












class GbsDaemonException(Exception):
    pass









    def doGet(self, userName, systemName, stageOnly):
        """
        out-obj {
            "state": str,             # enum, "idle" or other
            "stage": int,             # stage number
            "dumpe2fs": str,          # dumpe2fs for the system disk image file
            "rsync-port": int,        # 
            "ssh-port": int,          # 
            "ssh-public-key": str,    # 
            "ftp-port": int,          # optional
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)

        obj = self.sysDict.get((userName, systemName))

        if not stageOnly:
            if obj is not None:
                ret["state"] = obj.state
            else:
                ret["state"] = "idle"

        if obj is not None:
            ret["stage"] = obj.stage

        if not stageOnly:
            ret["dumpe2fs"] = 

        if obj is not None:
            if obj.rsyncPort is not None:
                ret["rsync-port"] = obj.rsyncPort

        if obj is not None:
            if obj.sshPort is not None:
                assert obj.sshPuKey is not None
                ret["ssh-port"] = obj.sshPort
                ret["ssh-public-key"] = obj.sshPubKey

        if obj is not None:
            if obj.ftpPort is not None:
                ret["ftp-port"] = obj.ftpPort

        return json.dumps(ret)

    def doPut(self, userName, systemName, clientArgs):
        """
        in-obj {
            "state": str,
        }
        in-obj {
            "stage": int,
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            GbsCommon.addSystem(userName, systemName)

        mode = clientArgs.get("state")
        if mode is not None:
            if mode == "idle":
                obj = self.sysDict.get((userName, systemName))
                if obj is not None:
                    self.sysObjClose(obj)
                    del self.sysDict[(userName, systemName)]
                else:
                    pass
            else:
                if (userName, systemName) not in self.sysDict:
                    self.sysDict[(userName, systemName)] = self.sysObjOpen(userName, systemName, mode)
                else:
                    raise GbsBusinessException(500)                     # fixme

        stage = clientArgs.get("stage")
        if stage is not None:
            try:
                stage = int(stage)
            except:
                raise GbsBusinessException(500)                     # fixme
            obj = self.sysDict.get((userName, systemName))
            if obj is None:
                raise GbsBusinessException(500)                     # fixme
            if stage != obj.stage + 1:
                raise GbsBusinessException(500)                     # fixme
            self.sysObjNextStage(obj)

    def doDelete(self, userName, systemName):
        if (userName, systemName) in self.sysDict:
            raise GbsBusinessException(500)                     # fixme
        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)
        GbsCommon.removeSystem(userName, systemName)

    def sysObjOpen(self, userName, systemName, state):
        sysObj.userName = userName
        sysObj.systemName = systemName
        sysObj.state = state
        sysObj.stage = 0
        sysObj.mntDir = GbsCommon.systemMountDisk(self.param, sysObj.userName, sysObj.systemName)


        return sysObj

    def sysObjClose(self, sysObj):
        pass

    def sysObjNextStage(self, sysObj):
        if sysObj.stage == 0:
        
        else:

        sysObj.stage += 1


class GbsBusinessException(Exception):
    def __init__(self, status_code, reason_phrase=None):
        self.statusCode = statusCode
        self.reason_phrase = reason_phrase


class _HandShakerConnInfo:
    serverSide = None            # bool
    state = None                # enum
    sslSock = None                # obj
    hostname = None                # str
    port = None                    # int
    spname = None              ""
        self.uuid = None







    def doGet(self, userName, systemName, stageOnly):
        """
        out-obj {
            "state": str,             # enum, "idle" or other
            "stage": int,             # stage number
            "dumpe2fs": str,          # dumpe2fs for the system disk image file
            "rsync-port": int,        # 
            "ssh-port": int,          # 
            "ssh-public-key": str,    # 
            "ftp-port": int,          # optional
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)

        obj = self.sysDict.get((userName, systemName))

        if not stageOnly:
            if obj is not None:
                ret["state"] = obj.state
            else:
                ret["state"] = "idle"

        if obj is not None:
            ret["stage"] = obj.stage

        if not stageOnly:
            ret["dumpe2fs"] = GbsCommon.systemDumpDiskInfo(self.param, userName, systemName)

        if obj is not None:
            if obj.rsyncPort is not None:
                ret["rsync-port"] = obj.rsyncPort

        if obj is not None:
            if obj.sshPort is not None:
                assert obj.sshPuKey is not None
                ret["ssh-port"] = obj.sshPort
                ret["ssh-public-key"] = obj.sshPubKey

        if obj is not None:
            if obj.ftpPort is not None:
                ret["ftp-port"] = obj.ftpPort

        return json.dumps(ret)

    def doPut(self, userName, systemName, clientArgs):
        """
        in-obj {
            "state": str,
        }
        in-obj {
            "stage": int,
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            GbsCommon.addSystem(userName, systemName)

        mode = clientArgs.get("state")
        if mode is not None:
            if mode == "idle":
                obj = self.sysDict.get((userName, systemName))
                if obj is not None:
                    self.sysObjClose(obj)
                    del self.sysDict[(userName, systemName)]
                else:
                    pass
            else:
                if (userName, systemName) not in self.sysDict:
                    self.sysDict[(userName, systemName)] = self.sysObjOpen(userName, systemName, mode)
                else:
                    raise GbsBusinessException(500)                     # fixme

        stage = clientArgs.get("stage")
        if stage is not None:
            try:
                stage = int(stage)
            except:
                raise GbsBusinessException(500)                     # fixme
            obj = self.sysDict.get((userName, systemName))
            if obj is None:
                raise GbsBusinessException(500)                     # fixme
            if stage != obj.stage + 1:
                raise GbsBusinessException(500)                     # fixme
            self.sysObjNextStage(obj)

    def doDelete(self, userName, systemName):
        if (userName, systemName) in self.sysDict:
            raise GbsBusinessException(500)                     # fixme
        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)
        GbsCommon.removeSystem(userName, systemName)

    def sysObjOpen(self, userName, systemName, state):
        sysObj.userName = userName
        sysObj.systemName = systemName
        sysObj.state = state
        sysObj.stage = 0
        sysObj.mntDir = GbsCommon.systemMountDisk(self.param, sysObj.userName, sysObj.systemName)


        return sysObj

    def sysObjClose(self, sysObj):
        pass

    def sysObjNextStage(self, sysObj):
        if sysObj.stage == 0:
        
        else:

        sysObj.stage += 1


class GbsBusinessException(Exception):
    def __init__(self, status_code, reason_phrase=None):
        self.statusCode = statusCode
        self.reason_phrase = reason_phrase




