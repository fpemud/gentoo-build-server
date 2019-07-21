#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import socket
import select
import struct
import threading
import subprocess
from gbs_util import GbsUtil


class CatFileService:

    def __init__(self, param, uuid, srcIp, srcCert, rootDir):
        self.param = param
        self.uuid = uuid
        self.srcIp = srcIp
        self.srcCert = srcCert
        self.rootDir = rootDir

        self.catfiledLogFile = os.path.join(self.param.logDir, uuid + "-catfiled.log")

        self.stunnelClientCertFile = os.path.join(self.param.tmpDir, uuid + "-cert.pem")
        self.stunnelCfgFile = os.path.join(self.param.tmpDir, uuid + "-stunnel.conf")
        self.stunnelRndFile = os.path.join(self.param.tmpDir, uuid + "-stunnel.rnd")
        self.stunnelLogFile = os.path.join(self.param.logDir, uuid + "-stunnel.log")

        self.catFilePort = None
        self.catFileThread = None

        self.stunnelPort = None
        self.stunnelProc = None

    def start(self):
        try:
            self.catFilePort = GbsUtil.getFreeTcpPort()
            self.catFileThread = _CatFileThread(self.catFilePort, self.catfiledLogFile, self.srcIp, self.srcCert, self.rootDir)
            self.catFileThread.start()
            GbsUtil.waitTcpPort(self.catFilePort)

            self.stunnelPort = GbsUtil.getFreeTcpPort()
            self.stunnelProc = self._runStunnelDaemon()
            GbsUtil.waitTcpPort(self.stunnelPort)
        except:
            self.stop()
            raise

    def stop(self):
        if self.stunnelProc is not None:
            self.stunnelProc.terminate()
            self.stunnelProc.wait()
        if self.catFileThread is not None:
            self.catFileThread.stop()
            self.catFileThread.join()
        GbsUtil.forceDelete(self.stunnelRndFile)
        GbsUtil.forceDelete(self.stunnelCfgFile)
        GbsUtil.forceDelete(self.stunnelClientCertFile)

    def getPort(self):
        return self.stunnelPort

    # def _genStunnelClientCert(self):
    #     with open(self.stunnelClientCertFile, "wb") as f:
    #         buf = crypto.dump_certificate(crypto.FILETYPE_PEM, self.srcCert)
    #         f.write(buf)
    #         os.fchmod(f.fileno(), 0o644)

    def _runStunnelDaemon(self):
        buf = ""
        buf += "debug = 6\n"
        buf += "output = %s\n" % (self.stunnelLogFile)
        buf += "\n"
        buf += "cert = %s\n" % (self.param.certFile)
        buf += "key = %s\n" % (self.param.privkeyFile)
        buf += "RNDfile = %s\n" % (self.stunnelRndFile)
        buf += "\n"
        buf += "client = no\n"
        buf += "foreground = yes\n"
        buf += "\n"
        buf += "[rsync]\n"
        buf += "accept = 0.0.0.0:%d\n" % (self.stunnelPort)
        buf += "connect = 127.0.0.1:%d\n" % (self.catFilePort)
        with open(self.stunnelCfgFile, "w") as f:
            f.write(buf)

        cmd = ""
        cmd += "/usr/sbin/stunnel \"%s\" 2>/dev/null" % (self.stunnelCfgFile)
        proc = subprocess.Popen(cmd, shell=True, universal_newlines=True)
        return proc


class _CatFileThread(threading.Thread):

    def __init__(self, port, logFile, srcIp, srcCert, rootDir):
        super().__init__()
        self.port = port
        self.logFile = logFile
        self.srcIp = srcIp
        self.srcCert = srcCert
        self.rootDir = rootDir
        self.serverSock = None

    def start(self):
        assert self.serverSock is None
        try:
            self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serverSock.bind(('0.0.0.0', self.port))
            self.serverSock.listen(1)
            self._log("catfiled started, server socket listen on port %d." % (self.port))
            super().start()
        except:
            self.stop()

    def stop(self):
        if self.serverSock is not None:
            self.serverSock.close()
            self.serverSock = None
            self._log("catfiled stopped, server socket closed.")

    def run(self):
        bHasError = False
        try:
            while True:
                if self.serverSock is None:
                    return

                # accept a socket
                readable, dummy, dummy = select.select([self.serverSock], [], [], 10.0)
                if readable == []:
                    continue
                sock, addr = self.serverSock.accept()
                sock.setblocking(0)
                self._log("accept session from %s." % (addr[0]))

                # process an accepted socket
                try:
                    # receive data format: fileNameBinaryBytesLen(4bytes) + fileNameAsBinaryBytesEncodedInUtf8
                    # send data format: successCode(1byte) + fileBinaryDataLen(8bytes) + fileBinaryData
                    # send error format: errorCode(1byte) + errorMessageBinaryBytesLen(8bytes) + errorMessageAsBinaryBytesEncodedInUtf8
                    fileNameLen = None
                    fileName = None
                    errCode = None
                    data = None
                    bCodeAndLenSent = None
                    buf = b''

                    while True:
                        inputs = []
                        outputs = []
                        if fileNameLen is None or fileName is None:
                            inputs.append(sock)
                        else:
                            outputs.append(sock)
                        readable, writable, exceptional = select.select(inputs, outputs, [sock], 10.0)
                        if exceptional != []:
                            raise Exception("socket exception")
                        if readable == [] and writable == []:
                            if self.serverSock is None:
                                return
                            continue

                        # receive filename length
                        if fileNameLen is None:
                            buf += sock.recv(struct.calcsize("!I") - len(buf))
                            if len(buf) < struct.calcsize("!I"):
                                if self.serverSock is None:
                                    return
                                continue
                            fileNameLen = struct.unpack("!I", buf)
                            buf = b''
                            self._log("    filename length received, %d." % (fileNameLen))

                        # receive filename
                        if fileName is None:
                            buf += sock.recv(fileNameLen - len(buf))
                            if len(buf) < fileNameLen:
                                if self.serverSock is None:
                                    return
                                continue
                            fileName = buf.decode("utf-8")
                            buf = b''
                            self._log("    filename received, %s." % (fileName))

                        # read file content
                        if data is None:
                            try:
                                with open(fileName, 'rb') as f:
                                    data = f.read()
                                errCode = 0
                                self._log("    read file completed, size %d." % (len(data)))
                            except Exception as e:
                                data = e.message.encode("utf-8")
                                errCode = 1
                                self._log("    read file failed, %s." % (e.message))
                            bCodeAndLenSent = False
                            buf = struct.pack("!cQ", errCode, len(data))

                        # send error code and data length
                        if not bCodeAndLenSent:
                            i = sock.send(buf)
                            buf = buf[i:]
                            if buf != b'':
                                if self.serverSock is None:
                                    return
                                continue
                            bCodeAndLenSent = True
                            self._log("    error code and data length sent.")

                        # send data
                        i = sock.send(data)
                        data = data[i:]
                        if data != b'':
                            if self.serverSock is None:
                                return
                            continue
                        sock.close()
                        self._log("    data sent, session closed.")
                        break
                except Exception as e:
                    sock.close()
                    self._log("    session closed on error %s." % (e.message))
                    break
        except Exception as e:
            if self.serverSock is not None:
                self.serverSock.close()
                self.serverSock = None
            self._log("catfiled terminated for error %s." % (e.message))
            bHasError = True
        finally:
            if not bHasError:
                self._log("catfiled terminated.")

    def _log(self, message):
        with open(self.logFile, "a") as f:
            f.write(message)
            f.write("\n")
