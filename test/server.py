#!/usr/bin/env python3

import gi
gi.require_version('Soup', '2.4')
from gi.repository import GLib
from gi.repository import Soup

    


def my_handler(server, msg, path, query, client):
    print("debgu1")
    msg.set_status(404)
    print("debgu2")


serv = Soup.Server()
serv.add_handler(None, my_handler)
serv.listen_local(8080, 0)


mainloop = GLib.MainLoop()
mainloop.run()










