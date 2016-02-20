#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class GbsClient:

    def __init__(self):
        self.clientUuid = None
        self.rootDir = None
        self.timeoutHandler = None
        self.rsyncProc = None
        self.rsyncPort = None
        self.rshProc = None
        self.rshPort = None
        self.ftpServer = None
        self.ftpPort = None


class GbsMain:

    def __init__(self, param):
        self.param = param
        self.clientDict = dict()

    def clientLogin(self, clientUuid):
        # create client object
        client = GbsClientInfo()
        client.clientUuid = clientUuid
        client.timeoutHandler = GLib.timeout_add_seconds(self.param.clientTimeoutInterval, self._clientTimeoutCallback, client)

        # set up servers
        try:
            client.rsyncPort = GbsUtil.getFreeTcpPort()
           
            client.rshPort = GbsUtil.getFreeTcpPort()
            
            client.ftpPort = GbsUtil.getFreeTcpPort()
            client.ftpServer = GbsUtil.FTPd(self.ftpPort, self.rootDir)
            client.ftpServer.start()
        except:
            if client.ftpServer is not None:
                client.ftpServert.stop()
            if client.rshProc is not None:
                client.rshProc.terminate()
                client.rshProc.wait()
            if client.rsyncProc is not None:
                client.rsyncProc.terminate()
                client.rsyncProc.wait()

        # record client object
        self.clientDict[clientUuid] = client
        return client

    def clientLogout(self, client):
        # delete client object
        del self.clientDict[client.clientUuid]

        # stop servers
        try:
            client.ftpServert.stop()
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

    def _clientTimeoutCallback(self, client):
        self.clientLogout(client)
        return False