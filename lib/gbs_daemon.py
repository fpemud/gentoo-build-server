#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class GbsDaemon:

    def __init__(self, param):
        self.param = param
        self.serverSocket = None
        self.serverSocketSourceId = None
        self.handshaker = None
        self.sessionDict = dict()
        self.mainloop = None

    def run(self):
        FrsUtil.mkDirAndClear(self.param.tmpDir)
        try:
            logging.getLogger().addHandler(logging.StreamHandler(sys.stderr))
            logging.getLogger().setLevel(GbsUtil.getLoggingLevel(self.param.logLevel))
            logging.info("Program begins.")

            # create main loop
            self.mainloop = GLib.MainLoop()

            # write pid file
            with open(self.param.pidFile, "w") as f:
                f.write(str(os.getpid()))

            # generate certificate and private key
            if not os.path.exists(self.param.certFile) or not os.path.exists(self.param.privkeyFile):
                GbsUtil.shell("/usr/bin/openssl req -new -x509 -key %s -out %s -days 36500" % (self.param.certFile, self.param.privkeyFile))
                logging.info('Certificate and private key generated.')
            else:
                logging.info('Certificate and private key found.')

            # start control server
            self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serverSock.bind(('0.0.0.0', port))
            self.serverSock.listen(5)
            self.serverSock.setblocking(0)
            self.serverSourceId = GLib.io_add_watch(self.serverSock, GLib.IO_IN | _flagError, self._onServerAccept)
            self.handshaker = _HandShaker(self.param.certFile, self.param.privkeyFile, self.param.certFile, self._onHandShakeComplete, self._onHandShakeError)
            logging.info('Control server started.')

            # start main loop
            logging.info("Mainloop begins.")
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, self._sigHandlerINT, None)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, self._sigHandlerTERM, None)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGUSR2, self._sigHandlerUSR2, None)    # let the process ignore SIGUSR2, we
            signal.siginterrupt(signal.SIGUSR2, True)                                               # use it to interrupt blocking system calls
            self.mainloop.run()
            logging.info("Mainloop exits.")
        finally:
            if self.soupServer is not None:
                self.serverSock.disconnect()
            for obj in self.sysDict.values():
                self.closeSys(obj)
            logging.shutdown()
            shutil.rmtree(self.param.runDir)
            logging.info("Program exits.")

    def _sigHandlerINT(self, signum):
        logging.info("SIGINT received.")
        self.mainloop.quit()
        return True

    def _sigHandlerTERM(self, signum)dict:
        logging.info("SIGTERM received.")
        self.mainloop.quit()
        return True

    def _sigHandlerUSR2(self, signum):
        return True

    def _onServerAccept(self, source, cb_condition):
        assert not (cb_condition & _flagError)
        assert source == self.serverSock

        try:
            new_sock, addr = self.serverSock.accept()
            self.handshaker.addSocket(new_sock, True)
            logging.info("Client \"%s\" accepted." % (addr))
            return True
        except socket.error as e:
            logging.error("Client accept failed, %s, %s", e.__class__, e)
            return True

    def _onHandShakeComplete(self, source, sslSock, hostname, port):
        logging.debug("Client \"%s\" hand shake complete." % (sslSock.getpeername()))

        sessionObj = GbsSession()
        sessionObj.uuid = GbsCommon.findOrCreateSystem(self.param, sslSock.get_peer_certificate().get_pubkey())
        sessionObj.plugin = None
        sessionObj.mode = None
        sessionObj.stage = None
        sessionObj.recvBuf = ""
        sessionObj.recvSourceId = GLib.io_add_watch(sslSock, GLib.IO_IN | _flagError, self._onRecv)
        self.sessionDict[sslSock] = sessionObj

    def _onHandShakeError(self, source, hostname, port):
        logging.error("Client \"%s\" hand shake error." % (source))
        source.close()

    def _onRecv(self, source, cb_condition):
        sessionObj = self.sessionDict[source]

        # 
        buf = source.recv(4096)
        if len(buf) == 0:


        








class GbsSession:

    def __init__(self):
        self.uuid = None
        self.plugin = None
        self.mode = None
        self.stage = None

        self.recvBuf = None
        self.recvSourceId = None











    def doGet(self, userName, systemName, stageOnly):
        """
        out-obj {
            "state": str,             # enum, "idle" or other
            "stage": int,             # stage number
            "dumpe2fs": str,          # dumpe2fs for the system disk image file
            "rsync-port": int,        # 
            "ssh-port": int,          # 
            "ssh-public-key": str,    # 
            "ftp-port": int,          # optional
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)

        obj = self.sysDict.get((userName, systemName))

        if not stageOnly:
            if obj is not None:
                ret["state"] = obj.state
            else:
                ret["state"] = "idle"

        if obj is not None:
            ret["stage"] = obj.stage

        if not stageOnly:
            ret["dumpe2fs"] = GbsCommon.systemDumpDiskInfo(self.param, userName, systemName)

        if obj is not None:
            if obj.rsyncPort is not None:
                ret["rsync-port"] = obj.rsyncPort

        if obj is not None:
            if obj.sshPort is not None:
                assert obj.sshPuKey is not None
                ret["ssh-port"] = obj.sshPort
                ret["ssh-public-key"] = obj.sshPubKey

        if obj is not None:
            if obj.ftpPort is not None:
                ret["ftp-port"] = obj.ftpPort

        return json.dumps(ret)

    def doPut(self, userName, systemName, clientArgs):
        """
        in-obj {
            "state": str,
        }
        in-obj {
            "stage": int,
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            GbsCommon.addSystem(userName, systemName)

        mode = clientArgs.get("state")
        if mode is not None:
            if mode == "idle":
                obj = self.sysDict.get((userName, systemName))
                if obj is not None:
                    self.sysObjClose(obj)
                    del self.sysDict[(userName, systemName)]
                else:
                    pass
            else:
                if (userName, systemName) not in self.sysDict:
                    self.sysDict[(userName, systemName)] = self.sysObjOpen(userName, systemName, mode)
                else:
                    raise GbsBusinessException(500)                     # fixme

        stage = clientArgs.get("stage")
        if stage is not None:
            try:
                stage = int(stage)
            except:
                raise GbsBusinessException(500)                     # fixme
            obj = self.sysDict.get((userName, systemName))
            if obj is None:
                raise GbsBusinessException(500)                     # fixme
            if stage != obj.stage + 1:
                raise GbsBusinessException(500)                     # fixme
            self.sysObjNextStage(obj)

    def doDelete(self, userName, systemName):
        if (userName, systemName) in self.sysDict:
            raise GbsBusinessException(500)                     # fixme
        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)
        GbsCommon.removeSystem(userName, systemName)

    def sysObjOpen(self, userName, systemName, state):
        sysObj.userName = userName
        sysObj.systemName = systemName
        sysObj.state = state
        sysObj.stage = 0
        sysObj.mntDir = GbsCommon.systemMountDisk(self.param, sysObj.userName, sysObj.systemName)


        return sysObj

    def sysObjClose(self, sysObj):
        pass

    def sysObjNextStage(self, sysObj):
        if sysObj.stage == 0:
        
        else:

        sysObj.stage += 1


class GbsBusinessException(Exception):
    def __init__(self, status_code, reason_phrase=None):
        self.statusCode = statusCode
        self.reason_phrase = reason_phrase


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
                raise _ConnException("Socket error, %s" % (SnUtil.cbConditionToStr(cb_condition)))

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
                peerName = SnUtil.getSslSocketPeerName(info.sslSock)
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
    state = None                # enum
    sslSock = None                # obj
    hostname = None                # str
    port = None                    # int
    spname = None              ""
        self.uuid = None







    def doGet(self, userName, systemName, stageOnly):
        """
        out-obj {
            "state": str,             # enum, "idle" or other
            "stage": int,             # stage number
            "dumpe2fs": str,          # dumpe2fs for the system disk image file
            "rsync-port": int,        # 
            "ssh-port": int,          # 
            "ssh-public-key": str,    # 
            "ftp-port": int,          # optional
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)

        obj = self.sysDict.get((userName, systemName))

        if not stageOnly:
            if obj is not None:
                ret["state"] = obj.state
            else:
                ret["state"] = "idle"

        if obj is not None:
            ret["stage"] = obj.stage

        if not stageOnly:
            ret["dumpe2fs"] = GbsCommon.systemDumpDiskInfo(self.param, userName, systemName)

        if obj is not None:
            if obj.rsyncPort is not None:
                ret["rsync-port"] = obj.rsyncPort

        if obj is not None:
            if obj.sshPort is not None:
                assert obj.sshPuKey is not None
                ret["ssh-port"] = obj.sshPort
                ret["ssh-public-key"] = obj.sshPubKey

        if obj is not None:
            if obj.ftpPort is not None:
                ret["ftp-port"] = obj.ftpPort

        return json.dumps(ret)

    def doPut(self, userName, systemName, clientArgs):
        """
        in-obj {
            "state": str,
        }
        in-obj {
            "stage": int,
        }
        """

        if not GbsCommon.hasSystem(userName, systemName):
            GbsCommon.addSystem(userName, systemName)

        mode = clientArgs.get("state")
        if mode is not None:
            if mode == "idle":
                obj = self.sysDict.get((userName, systemName))
                if obj is not None:
                    self.sysObjClose(obj)
                    del self.sysDict[(userName, systemName)]
                else:
                    pass
            else:
                if (userName, systemName) not in self.sysDict:
                    self.sysDict[(userName, systemName)] = self.sysObjOpen(userName, systemName, mode)
                else:
                    raise GbsBusinessException(500)                     # fixme

        stage = clientArgs.get("stage")
        if stage is not None:
            try:
                stage = int(stage)
            except:
                raise GbsBusinessException(500)                     # fixme
            obj = self.sysDict.get((userName, systemName))
            if obj is None:
                raise GbsBusinessException(500)                     # fixme
            if stage != obj.stage + 1:
                raise GbsBusinessException(500)                     # fixme
            self.sysObjNextStage(obj)

    def doDelete(self, userName, systemName):
        if (userName, systemName) in self.sysDict:
            raise GbsBusinessException(500)                     # fixme
        if not GbsCommon.hasSystem(userName, systemName):
            raise GbsBusinessException(404)
        GbsCommon.removeSystem(userName, systemName)

    def sysObjOpen(self, userName, systemName, state):
        sysObj.userName = userName
        sysObj.systemName = systemName
        sysObj.state = state
        sysObj.stage = 0
        sysObj.mntDir = GbsCommon.systemMountDisk(self.param, sysObj.userName, sysObj.systemName)


        return sysObj

    def sysObjClose(self, sysObj):
        pass

    def sysObjNextStage(self, sysObj):
        if sysObj.stage == 0:
        
        else:

        sysObj.stage += 1


class GbsBusinessException(Exception):
    def __init__(self, status_code, reason_phrase=None):
        self.statusCode = statusCode
        self.reason_phrase = reason_phrase


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
                raise _ConnException("Socket error, %s" % (SnUtil.cbConditionToStr(cb_condition)))

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
                peerName = SnUtil.getSslSocketPeerName(info.sslSock)
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
    state = None                # enum
    sslSock = None                # obj
    hostname = None                # str
    port = None                    # int
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








  # str


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








