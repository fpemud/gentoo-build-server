#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

from gbs_main import app


class MachineNotFound(Exception):

    @app.errorhandler(MachineNotFound)
    def error_handler(self, error):
        return "", 404


class MachineAlreadyExist(Exception):

    @app.errorhandler(MachineAlreadyExist)
    def error_handler(self, error):
        return "", 500


class MachineIsOpened(Exception):

    @app.errorhandler(MachineIsOpened)
    def error_handler(self, error):
        return "", 423


class MachineIsNotMyOwn(Exception):

    @app.errorhandler(MachineIsNotMyOwn)
    def error_handler(self, error):
        return "", 403