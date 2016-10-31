#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import uuid
import glob
from OpenSSL import crypto
from gbs_util import GbsUtil
import services.rsyncd
import services.sshd


class GbsProtocolException(Exception):
    pass


class GbsBusinessException(Exception):
    pass


class GbsPluginApi:

    ProtocolException = GbsProtocolException
    BusinessException = GbsBusinessException

    RsyncService = services.rsyncd.RsyncService
    SshService = services.sshd.SshService

    def __init__(self, sessObj):
        self.sessObj = sessObj

    def prepareRoot(self):
        procDir = os.path.join(self.sessObj.mntDir, "proc")
        sysDir = os.path.join(self.sessObj.mntDir, "sys")
        devDir = os.path.join(self.sessObj.mntDir, "dev")
        runDir = os.path.join(self.sessObj.mntDir, "run")
        tmpDir = os.path.join(self.sessObj.mntDir, "tmp")
        try:
            GbsUtil.shell("/bin/mount -t proc proc %s" % (procDir), "stdout")
            GbsUtil.shell("/bin/mount --rbind /sys %s" % (sysDir), "stdout")
            GbsUtil.shell("/bin/mount --make-rslave %s" % (sysDir), "stdout")
            GbsUtil.shell("/bin/mount --rbind /dev %s" % (devDir), "stdout")
            GbsUtil.shell("/bin/mount --make-rslave %s" % (devDir), "stdout")
            GbsUtil.shell("/bin/mount -t tmpfs tmpfs %s -o nosuid,nodev,mode=755" % (runDir), "stdout")
            GbsUtil.shell("/bin/mount -t tmpfs tmpfs %s -o nosuid,nodev" % (tmpDir), "stdout")
        except:
            self.unPrepareRoot()
            raise

    def unPrepareRoot(self):
        GbsUtil.shell("/bin/umount %s" % (os.path.join(self.sessObj.mntDir, "tmp")), "retcode+stdout")
        GbsUtil.shell("/bin/umount %s" % (os.path.join(self.sessObj.mntDir, "run")), "retcode+stdout")
        GbsUtil.shell("/bin/umount %s" % (os.path.join(self.sessObj.mntDir, "dev")), "retcode+stdout")
        GbsUtil.shell("/bin/umount %s" % (os.path.join(self.sessObj.mntDir, "sys")), "retcode+stdout")
        GbsUtil.shell("/bin/umount %s" % (os.path.join(self.sessObj.mntDir, "proc")), "retcode+stdout")


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
        GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse" % (fn, param.imageSizeUnit, param.defaultImageSize), "stdout")
        GbsUtil.shell("/sbin/mkfs.ext4 %s" % (fn), "stdout")

        return newUuid

    @staticmethod
    def systemGetDiskSize(param, uuid):
        sz = os.path.getsize(_image_file(param, uuid))
        assert sz % param.imageSizeUnit == 0
        return sz / param.imageSizeUnit

    @staticmethod
    def systemResizeDisk(param, uuid, newSize):
        fn = _image_file(param, uuid)
        sz = os.path.getsize(fn)
        assert sz % param.imageSizeUnit == 0
        newSize = newSize - sz / param.imageSizeUnit
        if newSize > 0:
            GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse,append" % (fn, param.imageSizeUnit, newSize), "stdout")
            GbsUtil.shell("/sbin/resize2fs %s" % (fn), "stdout")

    @staticmethod
    def systemDumpDiskInfo(param, userName, systemName):
        return GbsUtil.shell("/sbin/dumpe2fs -h %s" % (_image_file(param, userName, systemName))).decode("iso8859-1")

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


def _image_file(param, uuid):
    return os.path.join(param.cacheDir, uuid, "disk.img")


def _ssh_pubkey_file(param, uuid):
    return os.path.join(param.cacheDir, uuid, "pubkey.pem")


def _mnt_dir(param, uuid):
    return os.path.join(param.cacheDir, uuid, "mntdir")


def _default_image_size():
    return 0
