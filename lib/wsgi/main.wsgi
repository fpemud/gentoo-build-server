#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

@app.route("/<str:user_name>/<str:machine_name>", methods=["POST"])
def matchine_create(user_name, machine_name):
    return "Hello World!"

@app.route("/<str:user_name>/<str:machine_name>", methods=["GET"])
def machine_get_info(user_name, machine_name):
    return "Hello World!"

@app.route("/<str:user_name>/<str:machine_name>", methods=["DELETE"])
def matchine_delete(user_name, machine_name):
    return "Hello World!"

@app.route("/<str:user_name>/<str:machine_name>", methods=["PUT"])
def matchine_start_stop(user_name, machine_name):
    return "Hello World!"


