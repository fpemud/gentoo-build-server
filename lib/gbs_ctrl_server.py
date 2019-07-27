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
from gbs_common import GbsSystem
from gbs_common import GbsPluginApi
from gbs_common import GbsProtocolException
from gbs_common import GbsBusinessException
from services.catfiled import CatFileService
from services.rsyncd import RsyncService
from services.sshd import SshService


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
        self.serverSocketSourceId = GLib.io_add_watch(self.serverSock, GLib.IO_IN | _flagError, self.onServerAccept)
        self.handshaker = _HandShaker(self.param.certFile, self.param.privkeyFile, self.onHandShakeComplete, self.onHandShakeError)

    def stop(self):
        for sessObj in self.sessionDict.values():
            sessObj.stop()
        for sessObj in list(self.sessionDict.values()):     # remove element in loop, we must iterate a copied list
            sessObj.join()
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
        logging.info("Control Server: Client \"%s\" connected, UUID \"%s\"." % (sslSock.getpeername()[0], sessObj.sysObj.getUuid()))
        sessObj.start()
        self.sessionDict[sslSock] = sessObj

    def onHandShakeError(self, source, hostname, port):
        logging.error("Control Server: Client \"%s\" hand shake error." % (source.getpeername()[0]))
        source.close()


class GbsCtrlSession(threading.Thread):

    def __init__(self, parent, sslSock):
        super(GbsCtrlSession, self).__init__()

        self.parent = parent
        self.sslSock = sslSock
        self.recvBuf = b''
        self.sendBuf = b''
        self.bQuit = False

        # business data
        self.pubkey = self.sslSock.get_peer_certificate().get_pubkey()
        self.sysObj = GbsSystem(self.parent.param, self.pubkey)
        self.plugin = None                                                          # plugin object
        self.stage = None                                                           # stage name

    def stop(self):
        self.sslSock.shutdown()

    def run(self):
        try:
            while True:
                inputs = [self.sslSock]
                if len(self.sendBuf) > 0:
                    outputs = [self.sslSock]
                else:
                    outputs = []
                readable, writable, exceptional = select.select(inputs, outputs, inputs, 10.0)

                # read from client
                if len(readable) > 0 and not self.bQuit:
                    try:
                        buf = self.sslSock.recv(4096)
                        if len(buf) == 0:
                            logging.info("Control Server: Client \"%s\" disconnected." % (self._formatClient()))
                            return
                    except SSL.SysCallError as e:
                        if str(e) in ["(-1, 'Unexpected EOF')", "(104, 'ECONNRESET')"]:
                            logging.info("Control Server: Client \"%s\" disconnected." % (self._formatClient()))
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

                # write to client
                if len(writable) > 0:
                    i = self.sslSock.send(self.sendBuf)
                    self.sendBuf = self.sendBuf[i:]
                    if self.bQuit and len(self.sendBuf) == 0:
                        logging.info("Control Server: Client \"%s\" quits." % (self._formatClient()))
                        return

                # error occured
                if len(exceptional) > 0:
                    raise GbsCtrlSessionException("Socket error")

                # ensure the disk is always large enough
                self.sysObj.enlarge()
        except (GbsCtrlSessionException, GbsProtocolException, GbsBusinessException) as e:
            logging.error("Control Server: " + str(e) + " from client \"%s\"." % (self._formatClient()))
        finally:
            if self.stage == "syncup":
                self._syncupStageEndHandler()
            elif self.stage == "working":
                self._workingStageEndHandler()
            else:
                assert self.stage is None
            self._finiHandler()
            del self.parent.sessionDict[self.sslSock]
            self.sslSock.close()

    def onRequest(self, requestObj):
        if "command" not in requestObj:
            raise GbsProtocolException("Missing \"command\" in request object")

        if requestObj["command"] == "init":
            return self.cmdInit(requestObj)
        elif requestObj["command"] == "stage-syncup":
            return self.cmdStage("syncup", requestObj)
        elif requestObj["command"] == "stage-working":
            return self.cmdStage("working", requestObj)
        elif requestObj["command"] == "quit":
            return self.cmdQuit(requestObj)
        else:
            raise GbsProtocolException("Unknown command")

    def cmdInit(self, requestObj):
        logging.debug("Control Server: Command \"init\" received from client \"%s\"." % (self._formatClient()))
        try:
            self._initHandler(requestObj)
            logging.debug("Control Server: Command \"init\" processed from client \"%s\"." % (self._formatClient()))
            return {"return": {}}
        except Exception as e:
            self._finiHandler()
            logging.exception("Control Server: Command \"init\" error %s from client \"%s\"." % (str(e), self._formatClient()))
            return {"error": str(e)}

    def cmdStage(self, stage, requestObj):
        STAGE_LIST = ["syncup", "working"]
        assert stage in STAGE_LIST

        try:
            if STAGE_LIST.index(stage) == 0 and self.stage is not None:
                raise GbsProtocolException("Command \"stage-%s\" out of order" % (stage))
            if STAGE_LIST.index(stage) > 0 and STAGE_LIST.index(self.stage) + 1 != STAGE_LIST.index(stage):
                raise GbsProtocolException("Command \"stage-%s\" out of order" % (stage))

            # stage end processing
            if self.stage == "syncup":
                self._syncupStageEndHandler()
            elif self.stage == "working":
                self._workingStageEndHandler()
            else:
                assert self.stage is None

            # stage start processing
            logging.debug("Control Server: Command \"stage-%s\" received from client \"%s\"." % (stage, self._formatClient()))
            self.stage = stage
            try:
                if self.stage == "syncup":
                    ret = self._syncupStageStartHandler(requestObj)
                elif self.stage == "working":
                    ret = self._workingStageStartHandler(requestObj)
                else:
                    assert False
                logging.debug("Control Server: Command \"stage-%s\" processed from client \"%s\"." % (stage, self._formatClient()))
                return self._formatStageReturn(ret)
            except:
                if self.stage == "syncup":
                    self._syncupStageEndHandler()
                elif self.stage == "working":
                    self._workingStageEndHandler()
                else:
                    assert False
                self.stage = None
                raise
        except Exception as e:
            logging.exception("Control Server: Command \"stage-%s\" error %s from client \"%s\"." % (stage, str(e), self._formatClient()))
            return {"error": str(e)}

    def cmdQuit(self, requestObj):
        logging.debug("Control Server: Command \"quit\" from client \"%s\"." % (self._formatClient()))
        self.bQuit = True
        return {"return": {}}

    def _initHandler(self, requestObj):
        if "hostname" in requestObj:
            logging.debug("Control Server:     hostname = %s" % (requestObj["hostname"]))
            self.sysObj.getClientInfo().hostname = requestObj["hostname"]

        if "cpu-arch" in requestObj:
            logging.debug("Control Server:     cpu-arch = %s" % (requestObj["cpu-arch"]))
            self.sysObj.getClientInfo().cpu_arch = requestObj["cpu-arch"]
        else:
            raise GbsProtocolException("Missing \"cpu-arch\" in command \"init\"")

        if "plugin" in requestObj:
            logging.debug("Control Server:     plugin = %s" % (requestObj["plugin"]))
            pyfname = requestObj["plugin"].replace("-", "_")
            exec("import plugins.%s" % (pyfname))
            self.plugin = eval("plugins.%s.PluginObject(self.parent.param, GbsPluginApi(self.parent.param, self))" % (pyfname))

        self.sysObj.mount()
        self.sysObj.commitClientInfo()

        if self.plugin is not None and hasattr(self.plugin, "init_handler"):
            self.plugin.init_handler(requestObj)

    def _finiHandler(self):
        # should raise no exception
        if self.plugin is not None and hasattr(self.plugin, "fini_handler"):
            self.plugin.fini_handler()
        self.sysObj.unmount()

    def _syncupStageStartHandler(self, requestObj):
        ret = {}

        # invoke plugin start handler
        if self.plugin is not None and hasattr(self.plugin, "stage_syncup_start_handler"):
            ret2 = self.plugin.stage_syncup_start_handler(requestObj)
            GbsUtil.mergeDictWithOverwriteAsException(ret, ret2)

        # start rsync service
        self.rsyncServ = RsyncService(self.parent.param, self.sysObj.getUuid(), self.sslSock.getpeername()[0],
                                      self.sslSock.get_peer_certificate(), self.sysObj.getMntDir(), True)
        self.rsyncServ.start()
        logging.debug("Control Server:     rsync service on %d" % (self.rsyncServ.getPort()))
        GbsUtil.mergeDictWithOverwriteAsException(ret, {
            "rsync-port": self.rsyncServ.getPort(),
        })

        return ret

    def _syncupStageEndHandler(self):
        # should raise no exception
        if hasattr(self, "rsyncServ"):
            self.rsyncServ.stop()
            del self.rsyncServ
        if self.plugin is not None and hasattr(self.plugin, "stage_syncup_end_handler"):
            self.plugin.stage_syncup_end_handler()

    def _workingStageStartHandler(self, requestObj):
        ret = {}

        # prepare root directory
        self.sysObj.prepareRoot()

        # invoke plugin start handler
        if self.plugin is not None and hasattr(self.plugin, "stage_working_start_handler"):
            ret2 = self.plugin.stage_working_start_handler(requestObj)
            GbsUtil.mergeDictWithOverwriteAsException(ret, ret2)

        # start ssh service
        self.sshServ = SshService(self.parent.param, self.sysObj.getUuid(), self.sslSock.getpeername()[0],
                                  self.sslSock.get_peer_certificate(), self.sysObj.getMntDir())
        self.sshServ.start()
        logging.debug("Control Server:     ssh service on %d" % (self.sshServ.getPort()))
        GbsUtil.mergeDictWithOverwriteAsException(ret, {
            "ssh-port": self.sshServ.getPort(),
            "ssh-key": self.sshServ.getKey(),
        })

        # start rsync service
        self.rsyncServ = RsyncService(self.parent.param, self.sysObj.getUuid(), self.sslSock.getpeername()[0],
                                      self.sslSock.get_peer_certificate(), self.sysObj.getMntDir(), False)
        self.rsyncServ.start()
        logging.debug("Control Server:     rsync service on %d" % (self.rsyncServ.getPort()))
        GbsUtil.mergeDictWithOverwriteAsException(ret, {
            "rsync-port": self.rsyncServ.getPort(),
        })

        # start catfile service
        self.catfileServ = CatFileService(self.parent.param, self.sysObj.getUuid(), self.sslSock.getpeername()[0],
                                          self.sslSock.get_peer_certificate(), self.sysObj.getMntDir())
        self.catfileServ.start()
        logging.debug("Control Server:     catfile service on %d" % (self.catfileServ.getPort()))
        GbsUtil.mergeDictWithOverwriteAsException(ret, {
            "catfile-port": self.catfileServ.getPort(),
        })

        return ret

    def _workingStageEndHandler(self):
        # should raise no exception
        if hasattr(self, "catfileServ"):
            self.catfileServ.stop()
            del self.catfileServ
        if hasattr(self, "rsyncServ"):
            self.rsyncServ.stop()
            del self.rsyncServ
        if hasattr(self, "sshServ"):
            self.sshServ.stop()
            del self.sshServ
        if self.plugin is not None and hasattr(self.plugin, "stage_working_end_handler"):
            self.plugin.stage_working_end_handler()
        self.sysObj.unPrepareRoot()

    def _formatStageReturn(self, ret):
        ret["stage"] = self.stage
        return {"return": ret}

    def _formatClient(self):
        ret = "UUID:%s" % (self.sysObj.getUuid())
        if self.sysObj.getClientInfo().hostname is not None:
            ret = "%s(%s)" % (self.sysObj.getClientInfo().hostname, ret)
        return ret


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
                ctx = SSL.Context(SSL.TLSv1_2_METHOD)
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
