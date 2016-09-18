#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import sys
import pickle
import shutil
from gbs_util import GbsUtil
from gbs_param import GbsParam


class CommandObject:

	def __init__(self, param):
		self.param = param

	def cmdHasMachine(self, user_name, machine_name):
		return os.path.exists(os.path.join(self.param.varDir, user_name, machine_name)):
	
	def cmdCreateMachine(self, user_name, machine_name):
		path = os.path.join(self.param.varDir, user_name, machine_name)
		os.makedirs(path)

	def cmdDeleteMachine(self, user_name, machine_name):
		path = os.path.join(self.param.varDir, user_name, machine_name)
		shutil.rmtree(path)
	
	def execCommand(self, argv):
		try:
			funcObj = getattr(self, "cmd" + sys.argv[1][0].upper() + sys.argv[1][1:])	# "hasMachine" -> "cmdHasMachine"
			ret = funcObj(*sys.argv[2:])
			pickle.dump(sys.stdout, ret)
		except Exception as e:
			pickle.dump(sys.stderr, e)


CommandObject(GbsParam()).execCommand()
