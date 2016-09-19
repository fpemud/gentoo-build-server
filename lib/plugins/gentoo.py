#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class PluginObject:

    def __init__(self, mode):
        if mode not in ["emerge+sync", "emerge+binpkg"]:
            raise GbsPluginModeException()
        self.mode = mode

    def stageHandler(self, stage):
        pass
