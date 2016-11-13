#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import json
import socket
import select
import logging
import threading
from OpenSSL import SSL
from gi.repository import GLib
from gbs_util import GbsUtil
from gbs_common import GbsCommon
from gbs_common import GbsPluginApi
from gbs_common import GbsProtocolException
from gbs_common import GbsBusinessException
from services.rsyncd import RsyncService


class GbsCtrlServer:

    def __init__(self, param):
        self.param = param
        self.serverSocket = None
        self.serverSocketSourceId = None
        self.handshaker = None
        self.sessionDict = dict()

    def start(self):
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSock.bind(('0.0.0.0', self.param.ctrlPort))
        self.serverSock.listen(5)
        self.serverSourceId = GLib.io_add_watch(self.serverSock, GLib.IO_IN | _flagError, self.onServerAccept)
        self.handshaker = _HandShaker(self.param.certFile, self.param.privkeyFile, self.onHandShakeComplete, self.onHandShakeError)

    def stop(self):
        for sessObj in self.sessionDict.values():
            sessObj.stop()
        for sessObj in self.sessionDict.values():
            sessObj.waitForStop()
        self.serverSock.close()

    def onServerAccept(self, source, cb_condition):
        assert not (cb_condition & _flagError)
        assert source == self.serverSock

        try:
            new_sock, addr = self.serverSock.accept()
            new_sock.setblocking(0)
            self.handshaker.addSocket(new_sock)
            logging.info("Control Server: Client \"%s\" accepted." % (addr[0]))
            return True
        except socket.error as e:
            logging.error("Control Server: Client accept failed, %s, %s", e.__class__, e)
            return True

    def onHandShakeComplete(self, source, sslSock, hostname, port):
        pubkey = sslSock.get_peer_certificate().get_pubkey()
        for sessObj in self.sessionDict.values():
            if pubkey == sessObj.pubkey:
                logging.error("Control Server: Client \"%s\" duplicate, UUID \"%s\"." % (sslSock.getpeername()[0], self.sessionDict[pubkey].uuid))
                sslSock.close()
                return

        sessObj = GbsCtrlSession(self, sslSock)
        logging.info("Control Server: Client \"%s\" connected, UUID \"%s\"." % (sslSock.getpeername()[0], sessObj.uuid))
        self.sessionDict[sslSock] = sessObj

    def onHandShakeError(self, source, hostname, port):
        logging.error("Control Server: Client \"%s\" hand shake error." % (source.getpeername()[0]))
        source.close()


class GbsCtrlSession:

    def __init__(self, parent, sslSock):
        self.parent = parent
        self.sslSock = sslSock
        self.recvBuf = b''
        self.sendBuf = b''
        self.bQuit = False
        self.threadObj = threading.Thread(target=self.run)

        # business data
        self.pubkey = self.sslSock.get_peer_certificate().get_pubkey()
        self.uuid = GbsCommon.findOrCreateSystem(self.parent.param, self.pubkey)
        self.cpuArch = None                                                         # cpu architecture
        self.mntDir = None
        self.plugin = None                                                          # plugin object
        self.stage = None                                                           # stage number

        self.threadObj.start()

    def stop(self):
        self.sslSock.shutdown()

    def waitForStop(self):
        # this function should be called after stop
        self.threadObj.join()

    def run(self):
        try:
            while True:
                inputs = [self.sslSock]
                if len(self.sendBuf) > 0:
                    outputs = [self.sslSock]
                else:
                    outputs = []
                readable, writable, exceptional = select.select(inputs, outputs, inputs)

                if len(readable) > 0 and not self.bQuit:
                    try:
                        buf = self.sslSock.recv(4096)
                        if len(buf) == 0:
                            logging.info("Control Server: Client \"UUID:%s\" disconnects." % (self.uuid))
                            return
                    except SSL.SysCallError as e:
                        if str(e) == "(-1, 'Unexpected EOF')":
                            logging.info("Control Server: Client \"UUID:%s\" disconnects." % (self.uuid))
                            return
                        raise

                    self.recvBuf += buf

                    # we have received a json object, which must be a request
                    i = self.recvBuf.find(b'\n')
                    if i >= 0:
                        requestObj = json.loads(self.recvBuf[:i].decode("iso8859-1"))
                        self.recvBuf = self.recvBuf[i + 1:]
                        responseObj = self.onRequest(requestObj)    # create response when processing request
                        self.sendBuf += (json.dumps(responseObj) + "\n").encode("iso8859-1")

                if len(writable) > 0:
                    i = self.sslSock.send(self.sendBuf)
                    self.sendBuf = self.sendBuf[i:]
                    if self.bQuit and len(self.sendBuf) == 0:
                        logging.info("Control Server: Client \"UUID:%s\" quits." % (self.uuid))
                        return

                if len(exceptional) > 0:
                    raise GbsCtrlSessionException("Socket error")
        except (GbsCtrlSessionException, GbsProtocolException, GbsBusinessException) as e:
            logging.error("Control Server: " + str(e) + " from client \"UUID:%s\"." % (self.uuid))
        finally:
            if self.plugin is not None:
                assert self.stage is not None
                if self.stage == 1:
                    self._stage1EndHandler()                        # should raise no exception
                else:
                    self._invokePluginStageEndHandler(self.stage)   # should raise no exception
                self.plugin.disconnect_handler()                    # should raise no exception
            if self.mntDir is not None:
                GbsCommon.systemUnmountDisk(self.parent.param, self.uuid)
            del self.parent.sessionDict[self.sslSock]
            self.sslSock.close()

    def onRequest(self, requestObj):
        if "command" not in requestObj:
            raise GbsProtocolException("Missing \"command\" in request object")

        if requestObj["command"] == "init":
            return self.cmdInit(requestObj)
        elif requestObj["command"] == "stage":
            return self.cmdStage(requestObj)
        elif requestObj["command"] == "quit":
            return self.cmdQuit(requestObj)
        else:
            raise GbsProtocolException("Unknown command")

    def cmdInit(self, requestObj):
        try:
            if self.stage is not None:
                raise GbsProtocolException("Init command out of order")

            logging.debug("Control Server: Init command received from client \"UUID:%s\"." % (self.uuid))

            if "cpu-arch" not in requestObj:
                raise GbsProtocolException("Missing \"cpu-arch\" in init command")
            self.cpuArch = requestObj["cpu-arch"]

            if "size" not in requestObj:
                raise GbsProtocolException("Missing \"size\" in init command")
            if requestObj["size"] > self.parent.param.maxImageSize:
                raise GbsProtocolException("Value of \"size\" is too large in init command")
            self.size = requestObj["size"]
            GbsCommon.systemResizeDisk(self.parent.param, self.uuid, self.size)

            self.mntDir = GbsCommon.systemMountDisk(self.parent.param, self.uuid)

            if "plugin" not in requestObj:
                raise GbsProtocolException("Missing \"plugin\" in init command")
            pyfname = requestObj["plugin"].replace("-", "_")
            exec("import plugins.%s" % (pyfname))
            self.plugin = eval("plugins.%s.PluginObject(self.parent.param, GbsPluginApi(self))" % (pyfname))
            self.plugin.init_handler(requestObj)

            self.stage = 0
            logging.debug("Control Server: Init command processed from client \"UUID:%s\", plugin %s." % (self.uuid, requestObj["plugin"]))
            return {"return": {}}
        except Exception as e:
            logging.debug("Control Server: Init command error %s from client \"UUID:%s\"." % (str(e), self.uuid))
            if self.mntDir is not None:
                GbsCommon.systemUnmountDisk(self.parent.param, self.uuid)
            return {"error": str(e)}

    def cmdStage(self, requestObj):
        try:
            if self.stage is None:
                raise GbsProtocolException("Stage command out of order")

            logging.debug("Control Server: Stage command received from client \"UUID:%s\", stage:%d." % (self.uuid, self.stage))

            # stage end processing
            if self.stage == 0:
                pass
            elif self.stage == 1:
                self._stage1EndHandler()
            else:
                self._invokePluginStageEndHandler(self.stage)

            # stage start processing
            self.stage += 1
            try:
                ret = None
                if self.stage == 1:
                    ret = self._stage1StartHandler()
                elif self.stage > 1:
                    ret = self._invokePluginStageStartHandler(self.stage)
                else:
                    assert False
                logging.debug("Control Server: Stage command processed from client \"UUID:%s\", stage:%d." % (self.uuid, self.stage))
                return self._formatStageReturn(ret)
            except:
                self.stage -= 1
        except Exception as e:
            logging.exception("Control Server: Stage command error %s from client \"UUID:%s\"." % (str(e), self.uuid))
            return {"error": str(e)}

    def cmdQuit(self, requestObj):
        logging.debug("Control Server: Quit command from client \"UUID:%s\"." % (self.uuid))
        self.bQuit = True
        return {"return": {}}

    def _stage1StartHandler(self):
        try:
            self.rsyncServ = RsyncService(self.parent.param, self.uuid, self.sslSock.getpeername()[0],
                                          self.sslSock.get_peer_certificate(), self.mntDir, True)
            self.rsyncServ.start()
            return {"rsync-port": self.rsyncServ.getPort()}
        except:
            self._stage1EndHandler()
            raise

    def _stage1EndHandler(self):
        if hasattr(self, "rsyncServ"):
            self.rsyncServ.stop()
            del self.rsyncServ

    def _invokePluginStageStartHandler(self, stage):
        try:
            if hasattr(self.plugin, "stage_%d_start_handler" % (stage)):
                ret = eval("self.plugin.stage_%d_start_handler()" % (stage))
                return ret
            else:
                raise GbsPluginException("Stage %d is not supported" % (stage))
        except:
            self._invokePluginStageEndHandler(stage)
            raise

    def _invokePluginStageEndHandler(self, stage):
        if hasattr(self.plugin, "stage_%d_end_handler" % (stage)):
            eval("self.plugin.stage_%d_end_handler()" % (stage))

    def _formatStageReturn(self, ret):
        ret["stage"] = self.stage
        return {"return": ret}


class GbsCtrlSessionException(Exception):
    pass


class GbsPluginException(Exception):
    pass


class _HandShaker:

    HANDSHAKE_NONE = 0
    HANDSHAKE_WANT_READ = 1
    HANDSHAKE_WANT_WRITE = 2
    HANDSHAKE_COMPLETE = 3

    def __init__(self, certFile, privkeyFile, handShakeCompleteFunc, handShakeErrorFunc):
        self.certFile = certFile
        self.privkeyFile = privkeyFile
        self.handShakeCompleteFunc = handShakeCompleteFunc
        self.handShakeErrorFunc = handShakeErrorFunc
        self.sockDict = dict()

    def dispose(self):
        for sock in self.sockDict:
            sock.close()
        self.sockDict.clear()

    def addSocket(self, sock, hostname=None, port=None):
        info = _HandShakerConnInfo()
        info.state = _HandShaker.HANDSHAKE_NONE
        info.sslSock = None
        info.hostname = hostname
        info.port = port
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
                ctx.set_verify(SSL.VERIFY_PEER, _sslVerifyDummy)
#                ctx.set_mode(SSL.MODE_ENABLE_PARTIAL_WRITE)                    # fixme
                ctx.use_privatekey_file(self.privkeyFile)
                ctx.use_certificate_file(self.certFile)

                info.sslSock = SSL.Connection(ctx, source)
                info.sslSock.set_accept_state()
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
                    raise _ConnException("Handshake failed, %s" % (str(info.sslSock.getpeername())), e)

            # HANDSHAKE_COMPLETE
            if info.state == _HandShaker.HANDSHAKE_COMPLETE:
                # give socket to handShakeCompleteFunc
                self.handShakeCompleteFunc(source, self.sockDict[source].sslSock, self.sockDict[source].hostname, self.sockDict[source].port)
                del self.sockDict[source]
                return False
        except _ConnException as e:
            if not e.hasExcObj:
                logging.debug("_HandShaker._onEvent: %s, %s", e.message, str(info.sslSock.getpeername()))
            else:
                logging.debug("_HandShaker._onEvent: %s, %s, %s, %s", e.message, str(info.sslSock.getpeername()), e.excName, e.excMessage)
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
    return True


class _ConnException(Exception):

    def __init__(self, message, excObj=None):
        super(_ConnException, self).__init__(message)

        self.hasExcObj = False
        if excObj is not None:
            self.hasExcObj = True
            self.excName = excObj.__class__
            self.excMessage = excObj.message


class _HandShakerConnInfo:
    state = None                 # enum
    sslSock = None               # obj
    hostname = None              # str
    port = None                  # int


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


_flagError = GLib.IO_PRI | GLib.IO_ERR | GLib.IO_HUP | GLib.IO_NVAL
