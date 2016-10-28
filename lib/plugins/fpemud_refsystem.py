#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


class PluginObject:

    def __init__(self, param, api, sessObj):
        self.param = param
        self.api = api
        self.sessObj = sessObj
        self.mode = None

    def initHandler(self, requestObj):
        if "mode" not in requestObj:
            raise self.api.ProtocolException("Missing \"mode\" in init command")
        if requestObj["mode"] not in ["fpemud-refsystem-update"]:
            raise self.api.ProtocolException("Invalid \"mode\" in init command")
        self.mode = requestObj["mode"]

    def stageStartHandler(self, stage):
        if stage == 2:
            self.api.prepareRoot()
            self.sshServ = self.api.SshService(self.param, self.sessObj.uuid,
                                               self.sessObj.sslSock.getpeername()[0],
                                               self.sessObj.sslSock.get_peer_certificate(),
                                               self.sessObj.mntDir, [])
            self.sshServ.start()
            return {"return": {"ssh-port": self.sshServ.getPort()}}
        elif stage == 3:
            self.rsyncServ = self.api.RsyncService(self.param, self.sessObj.uuid,
                                                   self.sessObj.sslSock.getpeername()[0],
                                                   self.sslSock.get_peer_certificate(),
                                                   self.mntDir, False)
            self.rsyncServ.start()
            return {"return": {"rsync-port": self.rsyncServ.getPort()}}
        else:
            return {"return": {}}

    def stageEndHandler(self, stage):
        if stage == 2:
            self.sshServ.stop()
            del self.sshServ
            self.api.unPrepareRoot()
        elif stage == 3:
            self.rsyncServ.stop()
            del self.rsyncServ
        else:
            pass

    def disconnectHandler(self):
        pass
