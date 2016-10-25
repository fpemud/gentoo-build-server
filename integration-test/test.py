#!/usr/bin/env python2
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import dbus
import subprocess
import unittest
from client import TestClient


class Test_Init(unittest.TestCase):

    def setUp(self):
        self.client = TestClient()
        self.client.connect(2108)

    def runTest(self):
        obj = self.client.cmdInit("x86", 10, "gentoo")
        self.assertEqual(obj["return"], "")

    def tearDown(self):
        self.client.disconnect()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(Test_Init())
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest='suite')
