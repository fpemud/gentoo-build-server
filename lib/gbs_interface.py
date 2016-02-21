#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


class GbsMainObject:

    def __init__(self, param):
        self.param = param

    def login(self, clientUuid=None, clientName=None):
        clientIp = Pyro4.current_context.client.sock.getpeername()[0]
        client = self.param.mainObject.clientLogin(clientUuid, clientName, clientIp)
        return GbsSessionObject(self.param, client)


class GbsSessionObject:

    def __init__(self, param, client):
        self.param = param
        self.client = client

    def logout(self):
        self.param.mainObject.clientLogout(self.client)

    def getUuid(self):
        return self.client.uuid

    def getRsyncPort(self):
        return self.client.rsyncPort

    def getRshPort(self):
        return self.client.rshPort

    def getFtpPort(self):
        return self.client.ftpPort