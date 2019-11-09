#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
from gbs_util import GbsUtil
from gbs_param import GbsConst
from gbs_common import GbsSystemDatabase


class GbsCmd:

    def __init__(self, param):
        self.param = param

    def cmdInitialize(self):
        if not os.path.exists(GbsConst.varDir):
            os.makedirs(GbsConst.varDir)

        # auto generate certificate and private key
        cert, key = GbsUtil.genSelfSignedCertAndKey("syncupd", GbsConst.keySize)
        GbsUtil.dumpCertAndKey(cert, key, self.param.certFile, self.param.privkeyFile)

    def cmdShowClients(self):
        if not os.path.exists(GbsConst.runDir):
            raise Exception("not started")

        for uuid in GbsSystemDatabase.getUuidList(self.param):
            info = GbsSystemDatabase.getClientInfo(self.param, uuid)
            if info.hostname is not None:                               # fixme, should be removed in future
                print(info.hostname)
