#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
from gbs_util import GbsUtil
from gbs_common import GbsCommon


class GbsCmd:

    def __init__(self, param):
        self.param = param

    def cmdInitialize(self):
        if not os.path.exists(self.param.varDir):
            os.makedirs(self.param.varDir)

        # auto generate certificate and private key
        cert, key = GbsUtil.genSelfSignedCertAndKey("syncupd", self.param.keySize)
        GbsUtil.dumpCertAndKey(cert, key, self.param.certFile, self.param.privkeyFile)

    def cmdShowClients(self):
        if not os.path.exists(self.param.runDir):
            raise Exception("not started")

        for uuid in GbsCommon.getSystemUuidList(self.param):
            info = GbsCommon.systemGetClientInfo(self.param, uuid)
            if info.hostname is not None:                               # fixme, should be removed in future
                print(info.hostname)
