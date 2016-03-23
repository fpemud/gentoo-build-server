#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

from flask import Flask
from gbs_util import GbsUtil


app = Flask(__name__)
application = app              # wsgi interface
builderDict = dict()


@app.route("/<string:user_name>/<string:machine_name>", methods=["POST"])
def matchine_create(user_name, machine_name):
    if (user_name, machine_name) in builderDict:
        raise MachineIsOpened()
    if GbsUtil.execHelper("has-machine", user_name, machine_name) == "1":
        raise MachineAlreadyExist()

    global i
    i = i + 1
    return "Hello World! %d" % (i)


@app.route("/<string:user_name>/<string:machine_name>", methods=["GET"])
def machine_get_info(user_name, machine_name):
    global i
    i = i + 1
    return "Hello World! %d" % (i)


@app.route("/<string:user_name>/<string:machine_name>", methods=["DELETE"])
def matchine_delete(user_name, machine_name):
    if (user_name, machine_name) in builderDict:
        raise gbs_exception.MachineIsOpened()
    


    global i
    i = i + 1
    return "Hello World! %d" % (i)


@app.route("/<string:user_name>/<string:machine_name>", methods=["PUT"])
def matchine_start_stop(user_name, machine_name):
    global i
    i = i + 1
    return "Hello World! %d" % (i)


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