#!/bin/bash

ROOTDIR=$(realpath $(dirname $(realpath "$0"))/..)
BIN_FILES="${ROOTDIR}/syncupd"
LIB_FILES="$(find ${ROOTDIR}/lib -name '*.py' | tr '\n' ' ')"

autopep8 -ia --ignore=E402,E501 ${BIN_FILES}
autopep8 -ia --ignore=E402,E501 ${LIB_FILES}