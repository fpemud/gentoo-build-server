#!/usr/bin/env python2
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import dbus
import subprocess
import unittest
from client import TestClient
from client import TestRsync


class Test_Init(unittest.TestCase):

    def setUp(self):
        self.client = TestClient("./cert.pem", "./privkey.pem")
        self.client.connect(2108)

    def runTest(self):
        obj = self.client.cmdInit("x86", 10, "gentoo")
        self.assertEqual(obj["return"], {})

    def tearDown(self):
        self.client.dispose()


class Test_Quit(unittest.TestCase):

    def setUp(self):
        self.client = TestClient("./cert.pem", "./privkey.pem")
        self.client.connect(2108)

    def runTest(self):
        obj = self.client.cmdQuit()
        self.assertEqual(obj["return"], {})

    def tearDown(self):
        self.client.dispose()


class Test_Stage1(unittest.TestCase):

    def setUp(self):
        self.client = TestClient("./cert.pem", "./privkey.pem")
        self.rsync = TestRsync("./cert.pem", "./privkey.pem")
        self.client.connect(2108)

    def runTest(self):
        obj = self.client.cmdInit("x86", 10, "gentoo")
        self.assertEqual(obj["return"], {})

        obj = self.client.cmdStage()
        self.assertEqual(obj["return"]["stage"] == 1)
        self.assertTrue("rsync-port" in obj["return"])

        self.rsync.syncUp(".", "127.0.0.1", obj["return"]["rsync-port"])

    def tearDown(self):
        self.client.dispose()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(Test_Init())
    suite.addTest(Test_Quit())
    suite.addTest(Test_Stage1())
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest='suite')
