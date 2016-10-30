#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


class PluginObject:

    def __init__(self, param, api, sessObj):
        self.param = param
        self.api = api
        self.sessObj = sessObj
        self.mode = None

    def init_handler(self, requestObj):
        if "mode" not in requestObj:
            raise self.api.ProtocolException("Missing \"mode\" in init command")
        if requestObj["mode"] not in ["emerge+sync", "emerge+binpkg"]:
            raise self.api.ProtocolException("Invalid \"mode\" in init command")
        self.mode = requestObj["mode"]

    def stage_2_start_handler(self):
        self.api.prepareRoot()
        self.sshServ = self.api.SshService(self.param, self.sessObj.uuid,
                                           self.sessObj.sslSock.getpeername()[0],
                                           self.sessObj.sslSock.get_peer_certificate(),
                                           self.sessObj.mntDir, [])
        self.sshServ.start()
        return {"ssh-port": self.sshServ.getPort()}

    def stage_2_end_handler(self):
        if hasattr(self, "sshServ"):
            self.sshServ.stop()
            del self.sshServ
        self.api.unPrepareRoot()

    def stage_3_start_handler(self):
        if self.mode == "emerge+sync":
            self.rsyncServ = self.api.RsyncService(self.param, self.sessObj.uuid,
                                                    self.sessObj.sslSock.getpeername()[0],
                                                    self.sslSock.get_peer_certificate(),
                                                    self.mntDir, False)
            self.rsyncServ.start()
            return {"rsync-port": self.rsyncServ.getPort()}
        elif self.mode == "emerge+binpkg":
            assert False
        else:
            assert False

    def stage_3_end_handler(self):
        if self.mode == "emerge+sync":
            if hasattr(self, "rsyncServ"):
                self.rsyncServ.stop()
                del self.rsyncServ
        elif self.mode == "emerge+binpkg":
            assert False
        else:
            assert False

    def disconnect_handler(self):
        pass
