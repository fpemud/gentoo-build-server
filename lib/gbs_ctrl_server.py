#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


class GbsCtrlServer:

    def __init__(self, param, connectCallback, disconnectCallback, requestCallback):
        self.param = param
        self.connectCallback = connectCallback
        self.disconnectCallback = disconnectCallback
        self.requestCallback = requestCallback

        self.serverSocket = None
        self.serverSocketSourceId = None
        self.handshaker = None
        self.sessionDict = dict()

    def start(self):
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSock.bind(('0.0.0.0', port))
        self.serverSock.listen(5)
        self.serverSourceId = GLib.io_add_watch(self.serverSock, GLib.IO_IN | _flagError, self._onServerAccept)
        self.handshaker = _HandShaker(self.param.certFile, self.param.privkeyFile, self.param.certFile, self._onHandShakeComplete, self._onHandShakeError)

    def _onServerAccept(self, source, cb_condition):
        assert not (cb_condition & _flagError)
        assert source == self.serverSock

        try:
            new_sock, addr = self.serverSock.accept()
            new_sock.setblocking(0)
            self.handshaker.addSocket(new_sock, True)
            logging.info("Control Server: Client \"%s\" accepted." % (addr))
            return True
        except socket.error as e:
            logging.error("Control Server: Client accept failed, %s, %s", e.__class__, e)
            return True

    def _onHandShakeComplete(self, source, sslSock, hostname, port):
        logging.info("Control Server: Client \"%s\" hand shake complete." % (sslSock.getpeername()))
        obj = GbsCtrlSession()
        obj.recvBuf = ""
        obj.recvSourceId = GLib.io_add_watch(sslSock, GLib.IO_IN | _flagError, self._onRecv)
        obj.sendBuf = ""
        obj.sendSourceId = GLib.io_add_watch(sslSock, GLib.IO_OUT | _flagError, self._onSend)
        obj.privateData = self.connectCallback(sslSock.get_peer_certificate().get_pubkey())
        self.sessionDict[sslSock] = obj

    def _onHandShakeError(self, source, hostname, port):
        logging.error("Control Server: Client \"%s\" hand shake error." % (source))
        source.close()

    def _onRecv(self, source, cb_condition):
        sessObj = self.sessionDict[source]

        # receive from peer
        buf = source.recv(4096)

        # peer disconnects
        if len(buf) == 0:
            del self.sessionDict[source]
            self.disconnectCallback(sessObj.privateData)
            GLib.source_remove(sessObj.sendSourceId)
            GLib.source_remove(sessObj.recvSourceId)
            source.close()
            return False

        # save data to receive buffer
        sessObj.recvBuf += buf

        # we have received a json object, which must be a request
        i = sessObj.recvBuf.find("\n")
        if i >= 0:
            requestObj = json.loads(sessObj.recvBuf[:i])
            sessObj.recvBuf = sessObj.recvBuf[i+1:]
            responseObj = self.requestCallback(requestObj)
            source.send(json.dumps(responseObj))

        return True

    def _onSend(self, source, cb_condition):
        sessObj = self.sessionDict[source]



class GbsCtrlSession:

    def __init__(self):
        self.recvBuf = None
        self.recvSourceId = None
        self.sendBuf = None
        self.sendSourceId = None
        self.privateData = None

