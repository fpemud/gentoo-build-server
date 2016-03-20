#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

from routes import Mapper

map = Mapper()

map.connect(None, "/{user}/{machine}",
    controller="messages", action="create",
    conditions=dict(method=["POST"]))
map.connect("messages", "/messages",
    controller="messages", action="index",
    conditions=dict(method=["GET"]))
map.connect("formatted_messages", "/messages.{format}",
    controller="messages", action="index",
    conditions=dict(method=["GET"]))
map.connect("new_message", "/messages/new",
    controller="messages", action="new",
    conditions=dict(method=["GET"]))
map.connect("formatted_new_message", "/messages/new.{format}",
    controller="messages", action="new",
    conditions=dict(method=["GET"]))
map.connect("/messages/{id}",
    controller="messages", action="update",
    conditions=dict(method=["PUT"]))
map.connect("/messages/{id}",
    controller="messages", action="delete",
    conditions=dict(method=["DELETE"]))
map.connect("edit_message", "/messages/{id}/edit",
    controller="messages", action="edit",
    conditions=dict(method=["GET"]))
map.connect("formatted_edit_message", "/messages/{id}.{format}/edit",
    controller="messages", action="edit",
    conditions=dict(method=["GET"]))
map.connect("message", "/messages/{id}",
    controller="messages", action="show",
    conditions=dict(method=["GET"]))
map.connect("formatted_message", "/messages/{id}.{format}",
    controller="messages", action="show",
    conditions=dict(method=["GET"]))




map.connect(None, "/error/{action}/{id}", controller="error")
map.connect(None, "/", controller="main", action="index")

# Match a URL, returns a dict or None if no match
result = map.match('/error/myapp/4')
# result == {'controller': 'error', 'action': 'myapp', 'id': '4'}



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


