#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import uuid
import glob
from gbs_util import GbsUtil


class GbsCommon:

    @staticmethod
    def findOrCreateSystem(param, pubkey):
        # find system
        for fn in os.listdir(param.cacheDir):
            dirname = os.path.join(param.cacheDir, fn)
            with open(os.path.join(dirname, "pubkey")) as f:
                if pubkey == f.read():
                    return fn

        # create new system
        newUuid = uuid.UUID().hex
        dirname = os.path.join(param.cacheDir, newUuid)
        os.makedirs(dirname)

        # record public key
        with open(_ssh_pubkey_file(param, newUuid), "w") as f:
            f.write(pubkey)

        # generate disk image
        fn = _image_file(param, newUuid)
        GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse" % (fn, param.imageSizeUnit, param.defaultImageSize))
        GbsUtil.shell("/sbin/mkfs.ext4 %s" % (fn))

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
            GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse,append" % (fn, param.imageSizeUnit, newSize))
            GbsUtil.shell("/sbin/resize2fs %s" % (fn))

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
    def systemUnmountDisk(param, userName, systemName, mntDir):
        assert mntDir == _mnt_dir(param, userName, systemName)
        GbsUtil.shell("/bin/umount %s" % (mntDir))
        os.rmdir(mntDir)
        userDir = os.path.dirname(mntDir)
        if os.listdir(userDir) == []:
            os.rmdir(userDir)


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
