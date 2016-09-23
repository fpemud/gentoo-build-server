#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class PluginObject:

    def __init__(self, api, sessObj):
        self.api = api
        self.sessObj = sessObj
        self.mode = None

    def initHandler(self, requestObj):
        if "mode" not in requestObj:
            raise GbsDaemonException("Missing \"mode\" in init command")
        if requestObj["mode"] not in ["emerge+sync", "emerge+binpkg"]:
            raise self.api.GbsPluginException("Invalid \"mode\" in init command")
        self.mode = requestObj["mode"]

    def stageHandler(self):
        pass

    def disconnectHandler(self):
        pass