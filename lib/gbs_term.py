#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


class SnPeerServer:

    def __init__(self, certFile, privkeyFile, caCertFile, connectFunc):
        self.connectFunc = connectFunc
        self.handshaker = _HandShaker(certFile, privkeyFile, caCertFile, self._onHandShakeComplete, self._onHandShakeError)
        self.serverSock = None
        self.serverSourceId = None

    def dispose(self):
        if self.serverSock is not None:
            self.stop()
        self.handshaker.dispose()

    def start(self, port):
        assert self.serverSock is None

        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSock.bind(('0.0.0.0', port))
        self.serverSock.listen(5)
        self.serverSock.setblocking(0)
        self.serverSourceId = GLib.io_add_watch(self.serverSock, GLib.IO_IN | _flagError, self._onServerAccept)

    def stop(self):
        assert self.serverSock is not None

        ret = GLib.source_remove(self.serverSourceId)
        assert ret

        self.serverSock.close()
        self.serverSock = None

    def _onServerAccept(self, source, cb_condition):
        logging.debug("SnPeerServer._onServerAccept: Start, %s", SnUtil.cbConditionToStr(cb_condition))

        assert not (cb_condition & _flagError)
        assert source == self.serverSock

        try:
            new_sock, addr = self.serverSock.accept()
            self.handshaker.addSocket(new_sock, True)

            logging.debug("SnPeerServer._onServerAccept: End")
            return True
        except socket.error as e:
            logging.debug("SnPeerServer._onServerAccept: Failed, %s, %s", e.__class__, e)
            return True

    def _onHandShakeComplete(self, source, sslSock, hostname, port):
        logging.debug("SnPeerServer._onHandShakeComplete")
        self.connectFunc(sslSock)

    def _onHandShakeError(self, source, hostname, port):
        logging.debug("SnPeerServer._onHandShakeError")
        source.close()
