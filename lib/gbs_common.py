#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import uuid
from OpenSSL import crypto
from gbs_util import GbsUtil
from services.rsyncd import RsyncService
from services.sshd import SshService


class GbsProtocolException(Exception):
    pass


class GbsBusinessException(Exception):
    pass


class GbsPluginApi:

    ProtocolException = GbsProtocolException
    BusinessException = GbsBusinessException

    def __init__(self, param, sessObj):
        self.param = param
        self.sessObj = sessObj

        self.procDir = os.path.join(self.sessObj.mntDir, "proc")
        self.sysDir = os.path.join(self.sessObj.mntDir, "sys")
        self.devDir = os.path.join(self.sessObj.mntDir, "dev")
        self.runDir = os.path.join(self.sessObj.mntDir, "run")
        self.tmpDir = os.path.join(self.sessObj.mntDir, "tmp")
        self.varDir = os.path.join(self.sessObj.mntDir, "var")
        self.varTmpDir = os.path.join(self.varDir, "tmp")
        self.homeDirForRoot = os.path.join(self.sessObj.mntDir, "root")
        self.lostFoundDir = os.path.join(self.sessObj.mntDir, "lost+found")

        self.hasHomeDirForRoot = False
        self.hasVarDir = False

    def getUuid(self):
        return self.sessObj.uuid

    def getCpuArch(self):
        return self.sessObj.cpuArch

    def getIpAddress(self):
        return self.sessObj.sslSock.getpeername()[0]

    def getCertificate(self):
        return self.sessObj.sslSock.get_peer_certificate()

    def getPublicKey(self):
        return self.sessObj.pubkey

    def getRootDir(self):
        return self.sessObj.mntDir

    def prepareRoot(self):
        if os.path.exists(self.procDir):
            raise self.BusinessException("Redundant directory /proc is synced up")
        if os.path.exists(self.sysDir):
            raise self.BusinessException("Redundant directory /sys is synced up")
        if os.path.exists(self.devDir):
            raise self.BusinessException("Redundant directory /dev is synced up")
        if os.path.exists(self.runDir):
            raise self.BusinessException("Redundant directory /run is synced up")
        if os.path.exists(self.tmpDir):
            raise self.BusinessException("Redundant directory /tmp is synced up")
        if os.path.exists(self.varTmpDir):
            raise self.BusinessException("Redundant directory /var/tmp is synced up")
        if os.path.exists(self.lostFoundDir):
            raise self.BusinessException("Directory /lost+found should not exist")

        try:
            os.mkdir(self.procDir)
            GbsUtil.shell("/bin/mount -t proc proc %s" % (self.procDir), "stdout")

            os.mkdir(self.sysDir)
            GbsUtil.shell("/bin/mount --rbind /sys %s" % (self.sysDir), "stdout")
            GbsUtil.shell("/bin/mount --make-rslave %s" % (self.sysDir), "stdout")

            os.mkdir(self.devDir)
            GbsUtil.shell("/bin/mount --rbind /dev %s" % (self.devDir), "stdout")
            GbsUtil.shell("/bin/mount --make-rslave %s" % (self.devDir), "stdout")

            os.mkdir(self.runDir)
            GbsUtil.shell("/bin/mount -t tmpfs tmpfs %s -o nosuid,nodev,mode=755" % (self.runDir), "stdout")

            os.mkdir(self.tmpDir)
            os.chmod(self.tmpDir, 0o1777)
            GbsUtil.shell("/bin/mount -t tmpfs tmpfs %s -o nosuid,nodev" % (self.tmpDir), "stdout")

            if not os.path.exists(self.varDir):
                os.mkdir(self.varDir)
                self.hasVarDir = False
            else:
                self.hasVarDir = True

            os.mkdir(self.varTmpDir)

            if not os.path.exists(self.homeDirForRoot):
                os.mkdir(self.homeDirForRoot)
                os.chmod(self.homeDirForRoot, 0o700)
                self.hasHomeDirForRoot = False
            else:
                self.hasHomeDirForRoot = True
        except:
            self.unPrepareRoot()
            raise

    def unPrepareRoot(self):
        if not self.hasHomeDirForRoot:
            GbsUtil.forceDelete(self.homeDirForRoot)

        if not self.hasVarDir:
            GbsUtil.forceDelete(self.varDir)
        else:
            GbsUtil.forceDelete(self.varTmpDir)

        if os.path.exists(self.tmpDir):
            GbsUtil.shell("/bin/umount -l %s" % (self.tmpDir), "retcode+stdout")
            os.rmdir(self.tmpDir)

        if os.path.exists(self.runDir):
            GbsUtil.shell("/bin/umount -l %s" % (self.runDir), "retcode+stdout")
            os.rmdir(self.runDir)

        if os.path.exists(self.devDir):
            GbsUtil.shell("/bin/umount -l %s" % (self.devDir), "retcode+stdout")
            os.rmdir(self.devDir)

        if os.path.exists(self.sysDir):
            GbsUtil.shell("/bin/umount -l %s" % (self.sysDir), "retcode+stdout")
            os.rmdir(self.sysDir)

        if os.path.exists(self.procDir):
            GbsUtil.shell("/bin/umount -l %s" % (self.procDir), "retcode+stdout")
            os.rmdir(self.procDir)

    def startSshService(self, cmdPatternAllowed):
        self.sshServ = SshService(self.param, self.getUuid(), self.getIpAddress(),
                                  self.getCertificate(), self.getRootDir(), cmdPatternAllowed)
        self.sshServ.start()
        return (self.sshServ.getPort(), self.sshServ.getKey())

    def stopSshService(self):
        if hasattr(self, "sshServ"):
            self.sshServ.stop()
            del self.sshServ

    def startSyncDownService(self):
        self.rsyncServ = RsyncService(self.param, self.getUuid(), self.getIpAddress(),
                                      self.getCertificate(), self.getRootDir(), False)
        self.rsyncServ.start()
        return self.rsyncServ.getPort()

    def stopSyncDownService(self):
        if hasattr(self, "rsyncServ"):
            self.rsyncServ.stop()
            del self.rsyncServ


class GbsCommon:

    @staticmethod
    def findOrCreateSystem(param, pubkey):
        pubkey = crypto.dump_publickey(crypto.FILETYPE_PEM, pubkey)

        # ensure cache directory exists
        if not os.path.exists(param.cacheDir):
            os.makedirs(param.cacheDir)

        # find system
        for oldUuid in os.listdir(param.cacheDir):
            with open(_ssh_pubkey_file(param, oldUuid), "rb") as f:
                if pubkey == f.read():
                    return oldUuid

        # create new system
        newUuid = uuid.uuid4().hex
        dirname = os.path.join(param.cacheDir, newUuid)
        os.makedirs(dirname)

        # record public key
        with open(_ssh_pubkey_file(param, newUuid), "wb") as f:
            f.write(pubkey)

        # generate disk image
        fn = _image_file(param, newUuid)
#        GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse" % (fn, _gb(), param.imageSizeStep), "stdout")
        GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse" % (fn, _gb(), 40), "stdout")                              # fixme, on-line enlarg don't work
        GbsUtil.shell("/sbin/mkfs.ext4 -O ^has_journal %s" % (fn), "stdout")

        return newUuid

    @staticmethod
    def systemSetClientInfo(param, uuid, hostname):
        with open(_info_file(param, uuid), "w") as f:
            f.write("hostname = %s\n" % (hostname if hostname is not None else ""))

    @staticmethod
    def systemGetDiskSize(param, uuid):
        sz = os.path.getsize(_image_file(param, uuid))
        assert sz % param.imageSizeUnit == 0
        return sz / param.imageSizeUnit

    @staticmethod
    def systemEnlargeDisk(param, uuid):
        fn = _image_file(param, uuid)
        GbsUtil.shell("/sbin/resize2fs %s %dG" % (fn, os.path.getsize(fn) / _gb() + param.imageSizeStep))

    @staticmethod
    def systemGetSshPublicKey(param, userName, systemName):
        with open(_ssh_pubkey_file(param, userName, systemName), "r") as f:
            return f.read()

    @staticmethod
    def findSystemBySshPublicKey(param, key):
        for fn in os.listdir(param.varDir):
            if not fn.endswith(".pub"):
                continue
            with open(os.path.join(param.varDir, fn, "r")) as f:
                if f.read() == key:
                    m = re.search("^(.*)::(.*).pub$", fn)
                    assert m is not None
                    return (m.group(1), m.group(2))
        return None

    @staticmethod
    def systemMountDisk(param, uuid):
        dirname = _mnt_dir(param, uuid)
        GbsUtil.ensureDir(dirname)
        GbsUtil.shell("/bin/mount %s %s" % (_image_file(param, uuid), dirname))
        return dirname

    @staticmethod
    def systemUnmountDisk(param, uuid):
        dirname = _mnt_dir(param, uuid)
        GbsUtil.shell("/bin/umount -l %s" % (dirname))      # fixme, why "-l"?


def _gb():
    return 1024 * 1024 * 1024


def _info_file(param, uuid):
    return os.path.join(param.cacheDir, uuid, "client-info")


def _image_file(param, uuid):
    return os.path.join(param.cacheDir, uuid, "disk.img")


def _ssh_pubkey_file(param, uuid):
    return os.path.join(param.cacheDir, uuid, "pubkey.pem")


def _mnt_dir(param, uuid):
    return os.path.join(param.cacheDir, uuid, "mntdir")


def _default_image_size():
    return 0
