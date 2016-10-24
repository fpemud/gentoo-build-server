#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import json
import socket
import logging
from openssl import SSL
from gi.repository import GLib
from gbs_util import GbsUtil


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
        self.serverSock.bind(('0.0.0.0', self.param.port))
        self.serverSock.listen(5)
        self.serverSourceId = GLib.io_add_watch(self.serverSock, GLib.IO_IN | _flagError, self.onServerAccept)
        self.handshaker = _HandShaker(self.param.certFile, self.param.privkeyFile, self.param.certFile, self.onHandShakeComplete, self._onHandShakeError)

    def stop(self):
        for sslSock, sessObj in self.sessionDict.items():
            self._closeCtrlSession(sslSock, sessObj)
        self.serverSock.close()

    def closeSession(self, sessId):
        for sslSock, sessObj in self.sessionDict.items():
            if sessObj.id == sessId:
                self._closeCtrlSession(sslSock, sessObj)

    def onServerAccept(self, source, cb_condition):
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

    def onHandShakeComplete(self, source, sslSock, hostname, port):
        logging.info("Control Server: Client \"%s\" hand shake complete." % (sslSock.getpeername()))
        obj = GbsCtrlSession()
        obj.id = self._getCtrlSessionObjId()
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
            self._closeCtrlSession(source, sessObj)
            return False

        # save data to receive buffer
        sessObj.recvBuf += buf

        # we have received a json object, which must be a request
        i = sessObj.recvBuf.find("\n")
        if i >= 0:
            requestObj = json.loads(sessObj.recvBuf[:i])
            sessObj.recvBuf = sessObj.recvBuf[i + 1:]
            responseObj = self.requestCallback(sessObj.id, sessObj.privateData, requestObj)
            sessObj.sendBuf += json.dumps(responseObj)
            i = source.send(sessObj.sendBuf)
            sessObj.sendBuf = sessObj.sendBuf[i + 1:]

        return True

    def _onSend(self, source, cb_condition):
        sessObj = self.sessionDict[source]
        i = source.send(sessObj.sendBuf)
        sessObj.sendBuf = sessObj.sendBuf[i + 1:]
        return True

    def _getCtrlSessionObjId(self):
        id = 0
        for sessObj in self.sessionDict.values():
            id = max(sessObj.id, id)
        return id + 1

    def _closeCtrlSession(self, sslSock, sessObj):
        del self.sessionDict[sslSock]
        self.disconnectCallback(sessObj.id, sessObj.privateData)
        GLib.source_remove(sessObj.sendSourceId)
        GLib.source_remove(sessObj.recvSourceId)
        sslSock.close()


class GbsCtrlSession:

    def __init__(self):
        self.id = None
        self.recvBuf = None
        self.recvSourceId = None
        self.sendBuf = None
        self.sendSourceId = None
        self.privateData = None


class _HandShaker:

    HANDSHAKE_NONE = 0
    HANDSHAKE_WANT_READ = 1
    HANDSHAKE_WANT_WRITE = 2
    HANDSHAKE_COMPLETE = 3

    def __init__(self, certFile, privkeyFile, caCertFile, handShakeCompleteFunc, handShakeErrorFunc):
        self.certFile = certFile
        self.privkeyFile = privkeyFile
        self.caCertFile = caCertFile
        self.handShakeCompleteFunc = handShakeCompleteFunc
        self.handShakeErrorFunc = handShakeErrorFunc
        self.sockDict = dict()

    def dispose(self):
        for sock in self.sockDict:
            sock.close()
        self.sockDict.clear()

    def addSocket(self, sock, serverSide, hostname=None, port=None):
        info = _HandShakerConnInfo()
        info.serverSide = serverSide
        info.state = _HandShaker.HANDSHAKE_NONE
        info.sslSock = None
        info.hostname = hostname
        info.port = port
        info.spname = None                    # value of socket.getpeername()
        self.sockDict[sock] = info

        sock.setblocking(0)
        GLib.io_add_watch(sock, GLib.IO_IN | GLib.IO_OUT | _flagError, self._onEvent)

    def _onEvent(self, source, cb_condition):
        info = self.sockDict[source]

        try:
            # check error
            if cb_condition & _flagError:
                raise _ConnException("Socket error, %s" % (GbsUtil.cbConditionToStr(cb_condition)))

            # HANDSHAKE_NONE
            if info.state == _HandShaker.HANDSHAKE_NONE:
                ctx = SSL.Context(SSL.SSLv3_METHOD)
                if info.serverSide:
                    ctx.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT, _sslVerifyDummy)
                else:
                    ctx.set_verify(SSL.VERIFY_PEER, _sslVerifyDummy)
#                ctx.set_mode(SSL.MODE_ENABLE_PARTIAL_WRITE)                    # fixme
                ctx.use_privatekey_file(self.privkeyFile)
                ctx.use_certificate_file(self.certFile)
                ctx.load_verify_locations(self.caCertFile)

                info.spname = str(source.getpeername())
                info.sslSock = SSL.Connection(ctx, source)
                if info.serverSide:
                    info.sslSock.set_accept_state()
                else:
                    info.sslSock.set_connect_state()
                info.state = _HandShaker.HANDSHAKE_WANT_WRITE

            # HANDSHAKE_WANT_READ & HANDSHAKE_WANT_WRITE
            if ((info.state == _HandShaker.HANDSHAKE_WANT_READ and cb_condition & GLib.IO_IN) or
                    (info.state == _HandShaker.HANDSHAKE_WANT_WRITE and cb_condition & GLib.IO_OUT)):
                try:
                    info.sslSock.do_handshake()
                    info.state = _HandShaker.HANDSHAKE_COMPLETE
                except SSL.WantReadError:
                    info.state = _HandShaker.HANDSHAKE_WANT_READ
                except SSL.WantWriteError:
                    info.state = _HandShaker.HANDSHAKE_WANT_WRITE
                except SSL.Error as e:
                    raise _ConnException("Handshake failed, %s" % (_handshake_info_to_str(info)), e)

            # HANDSHAKE_COMPLETE
            if info.state == _HandShaker.HANDSHAKE_COMPLETE:
                # check peer name
                peerName = GbsUtil.getSslSocketPeerName(info.sslSock)
                if info.serverSide:
                    if peerName is None:
                        raise _ConnException("Hostname incorrect, %s, %s" % (_handshake_info_to_str(info), peerName))
                else:
                    if peerName is None or peerName != info.hostname:
                        raise _ConnException("Hostname incorrect, %s, %s" % (_handshake_info_to_str(info), peerName))

                # give socket to handShakeCompleteFunc
                self.handShakeCompleteFunc(source, self.sockDict[source].sslSock, self.sockDict[source].hostname, self.sockDict[source].port)
                del self.sockDict[source]
                return False
        except _ConnException as e:
            if not e.hasExcObj:
                logging.debug("_HandShaker._onEvent: %s, %s", e.message, _handshake_info_to_str(info))
            else:
                logging.debug("_HandShaker._onEvent: %s, %s, %s, %s", e.message, _handshake_info_to_str(info), e.excName, e.excMessage)
            self.handShakeErrorFunc(source, self.sockDict[source].hostname, self.sockDict[source].port)
            del self.sockDict[source]
            return False

        # register io watch callback again
        if info.state == _HandShaker.HANDSHAKE_WANT_READ:
            GLib.io_add_watch(source, GLib.IO_IN | _flagError, self._onEvent)
        elif info.state == _HandShaker.HANDSHAKE_WANT_WRITE:
            GLib.io_add_watch(source, GLib.IO_OUT | _flagError, self._onEvent)
        else:
            assert False

        return False


def _sslVerifyDummy(conn, cert, errnum, depth, ok):
    return ok


class _ConnException(Exception):

    def __init__(self, message, excObj=None):
        super(_ConnException, self).__init__(message)

        self.hasExcObj = False
        if excObj is not None:
            self.hasExcObj = True
            self.excName = excObj.__class__
            self.excMessage = excObj.message


class _HandShakerConnInfo:
    serverSide = None            # bool
    state = None                 # enum
    sslSock = None               # obj
    hostname = None              # str
    port = None                  # int
    spname = None                # str


def _handshake_state_to_str(handshake_state):
    if handshake_state == _HandShaker.HANDSHAKE_NONE:
        return "NONE"
    elif handshake_state == _HandShaker.HANDSHAKE_WANT_READ:
        return "WANT_READ"
    elif handshake_state == _HandShaker.HANDSHAKE_WANT_WRITE:
        return "WANT_WRITE"
    elif handshake_state == _HandShaker.HANDSHAKE_COMPLETE:
        return "COMPLETE"
    else:
        assert False


def _handshake_info_to_str(info):
    if info.serverSide:
        return info.spname
    else:
        return "%s, %d" % (info.hostname, info.port)


_flagError = GLib.IO_PRI | GLib.IO_ERR | GLib.IO_HUP | GLib.IO_NVAL
