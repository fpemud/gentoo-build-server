#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class GbsClient:

    def __init__(self):
        self.uuid = None
        self.name = None
        self.ip = None
        self.lastLogin = None
        self.rootDir = None
        self.timeoutHandler = None
        self.rsyncProc = None
        self.rsyncPort = None
        self.rshProc = None
        self.rshPort = None
        self.ftpServer = None
        self.ftpPort = None


class GbsClientData:

    def __init__(self):
        self.uuid = None
        self.name = None
        self.lastLogin = None


class GbsMain:

    def __init__(self, param):
        self.param = param
        self.clientDict = dict()

    def clientLogin(self, clientUuid, clientName, clientIp):
        if clientUuid is not None and not self.clientExists(clientUuid):
            raise Exception("the specified client %s does not exist" % (clientUuid))

        # create client object
        client = GbsClientInfo()
        if clientUuid is not None:
            client.uuid = clientUuid
        else:
            client.uuid = uuid.uuid4()
        if clientName is not None:
            client.name = clientName
        else:
            client.name = ""
        client.ip = clientIp
        client.lastLogin = datetime.now()
        client.rootDir = os.path.join(self.param.varDir, clientUuid)

        # record client in database
        self._saveClientToDb(client)

        try:
            # create client root directory
            if not os.path.exists(client.rootDir):
                os.makedirs(client.rootDir)

            # set up rsync server
            client.rsyncPort = GbsUtil.getFreeTcpPort()
            client.rsyncProc = self._runRsyncDaemon(client)
           
            # set up rsh server
            client.rshPort = GbsUtil.getFreeTcpPort()
            client.rshProc = self._runRshServer(client)
            
            # set up ftp server
            client.ftpPort = GbsUtil.getFreeTcpPort()
            client.ftpServer = GbsUtil.FTPd(client.ftpPort, client.rootDir, client.ip)
            client.ftpServer.start()

            # add timeout handler
            client.timeoutHandler = GLib.timeout_add_seconds(self.param.clientTimeoutInterval, self._clientTimeoutCallback, client)

            # record client
            self.clientDict[clientUuid] = client
            return client
        except:
            if client.timeoutHandler is not None:
                GLib.source_remove(client.timeoutHandler)
            if client.ftpServer is not None:
                client.ftpServert.stop()
            if client.rshProc is not None:
                client.rshProc.terminate()
                client.rshProc.wait()
            if client.rsyncProc is not None:
                client.rsyncProc.terminate()
                client.rsyncProc.wait()
            raise

    def clientLogout(self, client):
        # delete client object
        del self.clientDict[client.uuid]

        GLib.source_remove(client.timeoutHandler)

        try:
            client.ftpServer.stop()
        except:
            pass
        try:
            client.rshProc.terminate()
            client.rshProc.wait()
        except:
            pass
        try:
            client.rsyncProc.terminate()
            client.rsyncProc.wait()
        except:
            pass

    def clientResetTimeout(self, client):
        GLib.source_remove(client.timeoutHandler)
        client.timeoutHandler = GLib.timeout_add_seconds(self.param.clientTimeoutInterval, self._clientTimeoutCallback, client)

    def clientExists(self, clientUuid):
        if not os.path.exists(os.path.join(self.param.varDir, clientUuid)):
            return False
        return True

    def _clientTimeoutCallback(self, client):
        self.clientLogout(client)
        return False

    def _runRsyncDaemon(self, client):
        # generate configuration file
        cfgf = os.path.join(self.param.tmpDir, "%s-rsync.conf" % (client.uud))
        with open(cfgf, "w") as f:
            f.write("[main]\n")
            f.write("path = %s\n" % (client.rootDir))
            f.write("read only = no\n")
            f.write("hosts allow = %s\n" % (client.ip))
            f.write(")

        # run rsync process
        cmd = ""
        cmd += "/usr/bin/rsync "
        cmd += "--daemon --no-detach "
        cmd += "--config=%s " % (cfgf)
        cmd += "--port=%d " % (client.rsyncPort)
        cmd += "> %s/%s-rsync.out 2>&1" % (self.param.tmpDir, client.uuid)
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)

        return proc
        
    def _runRshServer(self, client):
        return None

    def _saveClientToDb(self, client):
        ret = pickle.load(self.param.clientDataFile)
        if client.uuid in ret:
            ret[client.uuid].name = client.name
            ret[client.uuid].lastLogin = client.lastLogin
        else:
            obj = GbsClientData()
            obj.uuid = client.uuid
            obj.name = client.name
            obj.lastLogin = client.lastLogin
            ret[client.uuid] = obj
        pickle.dump(ret, self.param.clientDataFile)

    def _loadClientDataFromDb(self, clientUuid):
        ret = pickle.load(self.param.clientDataFile)
        return ret.get(clientUuid)