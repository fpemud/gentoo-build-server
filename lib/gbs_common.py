#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import uuid
import glob
from OpenSSL import crypto
from gbs_util import GbsUtil


class GbsProtocolException(Exception):
    pass


class GbsBusinessException(Exception):
    pass


class GbsPluginApi:

    ProtocolException = GbsProtocolException
    BusinessException = GbsBusinessException

    def __init__(self, parent):
        self.parent = parent


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
    def hasSystem(param, userName, systemName):
        return glob.glob(_glob_var(param, userName, systemName)) != []

    @staticmethod
    def addSystem(param, userName, systemName):
        assert glob.glob(_glob_var(param, userName, systemName)) == []
        assert glob.glob(_glob_cache(param, userName, systemName)) == []

        # generate ssh public key
        fn = _ssh_pubkey_file(param, userName, systemName)

        # generate disk image
        fn = _image_file(param, userName, systemName)
        GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse" % (fn, 1024 * 1024 * 1024, 50))   # allocate 50GB
        GbsUtil.shell("/sbin/mkfs.ext4 %s" % (fn))

    @staticmethod
    def removeSystem(param, userName, systemName):
        # delete cache files
        GbsUtil.shell("/bin/rm -f %s" % (_glob_cache(param, userName, systemName)))
        GbsUtil.shell("/bin/rm -f %s" % (_glob_var(param, userName, systemName)))

    @staticmethod
    def systemDumpDiskInfo(param, userName, systemName):
        return GbsUtil.shell("/sbin/dumpe2fs -h %s" % (_image_file(param, userName, systemName))).decode("iso8859-1")

    @staticmethod
    def systemGetSshPublicKey(param, userName, systemName):
        with open(_ssh_pubkey_file(param, userName, systemName), "r") as f:
            return f.read()

    @staticmethod
    def systemIsActive(param, userName, systemName):
        return False

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
        os.makedirs(dirname)
        GbsUtil.shell("/bin/mount %s %s" % (_image_file(param, uuid), dirname))
        return dirname

    @staticmethod
    def systemUnmountDisk(param, uuid):
        dirname = _mnt_dir(param, uuid)
        GbsUtil.shell("/bin/umount %s" % (dirname))
        os.rmdir(dirname)


def _image_file(param, uuid):
    return os.path.join(param.cacheDir, uuid, "disk.img")


def _ssh_pubkey_file(param, uuid):
    return os.path.join(param.cacheDir, uuid, "pubkey.pem")


def _mnt_dir(param, uuid):
    return os.path.join(param.tmpDir, uuid, "mnt")


def _glob_var(param, userName, systemName):
    return os.path.join(param.varDir, "%s::%s.*" % (userName, systemName))


def _glob_cache(param, userName, systemName):
    return os.path.join(param.varDir, "%s::%s.*" % (userName, systemName))


def _default_image_size():
    return 0
