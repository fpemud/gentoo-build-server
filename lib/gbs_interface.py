#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


class GbsMainObject:

    def __init__(self, param):
        self.param = param

    def login(self, clientUuid):
        client = self.param.mainObject.clientLogin(clientUuid)
        return GbsSessionObject(self.param, client)


class GbsSessionObject:

    def __init__(self, param, client):
        self.param = param
        self.client = client

    def logout(self):
        self.param.mainObject.clientLogout(client)

    def getRsyncPort(self):
        return client.rsyncPort

    def getRshPort(self):
        return client.rshPort

    def getFtpPort(self):
        return client.ftpPort