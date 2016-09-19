#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

class GbsCommon:

    @staticmethod
    def genOrLoadKey(self, ktype):
        kf = os.path.join(self.param.varDir, "host_%s_key" % (ktype))

        while os.path.exists(kf):
            if ktype == "dsa":
                host_key = paramiko.dsskey.DSSKey.from_private_key_file(kf)
                if host_key.get_bits() != self.param.dsa_bits:
                    break
            elif ktype == "rsa":
                host_key = paramiko.rsakey.RSAKey.from_private_key_file(kf)
                if host_key.get_bits() != self.param.rsa_bits:
                    break
            elif ktype == "ecdsa":
                host_key = paramiko.ecdsakey.ECDSAKey.from_private_key_file(kf)
                if host_key.get_bits() != self.param.ecdsa_bits:
                    break
            else:
                assert False
            logging.info('%s host key loaded from \"%s\".' % (ktype.upper(), kf))
            return host_key

        if ktype == "dsa":
            host_key = paramiko.DSSKey.generate(bits=self.param.dsa_bits)
        elif ktype == "rsa":
            host_key = paramiko.RSAKey.generate(bits=self.param.rsa_bits)
        elif ktype == "ecdsa":
            host_key = paramiko.ECDSAKey.generate()
        else:
            assert False
        host_key.write_private_key_file(kf)
        os.chmod(kf, 0o600)
        logging.info('%s host key generated and saved into \"%s\".' % (ktype.upper(), kf))
        return host_key

    @staticmethod
    def isUserNameValid(userName):
        # from is_valid_name() in shadow-utils-4.1
        return re.search("^[a-z_][a-z0-9_-]*$") is not None

    @staticmethod
    def isSystemNameValid(userName):
        # from RFC1123
        return re.search("^[a-z0-9][a-z0-9-]*$") is not None

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

def _image_file(param, userName, systemName):
    return os.path.join(self.param.cacheDir, "%s::%s.disk" % (userName, systemName))


def _ssh_pubkey_file(param, userName, systemName):
    return os.path.join(self.param.varDir, "%s::%s.pub" % (userName, systemName))


def _glob_var(param, userName, systemName):
    return os.path.join(self.param.varDir, "%s::%s.*" % (userName, systemName))


def _glob_cache(param, userName, systemName):
    return os.path.join(self.param.varDir, "%s::%s.*" % (userName, systemName))

def _mnt_dir(param, userName, systemName):
    return os.path.join(self.tmpDir, userName, systemName)


