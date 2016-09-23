#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-


class GbsCommon:

    @staticmethod
    def findOrCreateSystem(param, pubkey):
        # find system
        for fn in os.listdir(self.param.cacheDir):
            dirname = os.path.join(self.param.cacheDir, fn)
            with open(os.path.join(dirname, "pubkey")) as f:
                if pubkey == f.read():
                    return fn

        # create new system
        uuid = uuid.UUID().hex
        dirname = os.path.join(self.param.cacheDir, uuid)
        os.makedirs(dirname)

        # record public key
        with open(_ssh_pubkey_file(param, uuid), "w") as f:
            f.write(pubkey)

        # generate disk image
        fn = _image_file(param, uuid)
        GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse" % (fn, self.param.imageSizeUnit, self.param.defaultImageSize))
        GbsUtil.shell("/sbin/mkfs.ext4 %s" % (fn))

        return uuid

    @staticmethod
    def systemGetDiskSize(param, uuid):
        sz = os.path.getsize(_image_file(param, uuid))
        assert sz % self.param.imageSizeUnit == 0
        return sz / self.param.imageSizeUnit

    @staticmethod
    def systemResizeDisk(param, uuid, newSize):
        fn = _image_file(param, uuid)
        sz = os.path.getsize(fn)
        assert sz % self.param.imageSizeUnit == 0
        newSize = newSize - sz / self.param.imageSizeUnit
        if newSize > 0:
            GbsUtil.shell("/bin/dd if=/dev/zero of=%s bs=%d count=%s conv=sparse,append" % (fn, self.param.imageSizeUnit, newSize)) 
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

    @staticmethod
    def findSystemBySshPublicKey(param, key):
        for fn in os.listdir(self.param.varDir):
            if not fn.endswith(".pub"):
                continue
            with open(os.path.join(self.param.varDir, fn, "r") as f:
                if f.read() == key:
                    m = re.search("^(.*)::(.*).pub$", fn)
                    assert m is not None
                    return (m.group(1), m.group(2))
        return None

    @staticmethod
    def systemMountDisk(param, userName, systemName):
        dirname = _mnt_dir(param, userName, systemName)
        os.makedirs(dirname)
        GbsUtil.shell("/bin/mount %s %s" % (_image_file(param, userName, systemName), dirname))
        return dirname

    @staticmethod
    def systemUnmountDisk(param, userName, systemName, mntDir):
        assert mntDir == _mnt_dir(param, userName, systemName)
        GbsUtil.shell("/bin/umount %s" % (dirname))
        os.rmdir(mntDir)
        userDir = os.path.dirname(mntDir)
        if os.listdir(userDir) == []:
            os.rmdir(userDir)


def _image_file(param, uuid):
    return os.path.join(self.param.cacheDir, uuid, "disk.img")


def _ssh_pubkey_file(param, userName, systemName):
    return os.path.join(self.param.cacheDir, uuid, "pubkey.pem")


def _glob_var(param, userName, systemName):
    return os.path.join(self.param.varDir, "%s::%s.*" % (userName, systemName))


def _glob_cache(param, userName, systemName):
    return os.path.join(self.param.varDir, "%s::%s.*" % (userName, systemName))

def _mnt_dir(param, userName, systemName):
    return os.path.join(self.tmpDir, userName, systemName)


def _default_image_size():
