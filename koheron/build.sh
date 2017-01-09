#!/bin/bash

set -e

KOHERON_SDK_PATH=$1
INSTRUMENT_DIR=$2
INSTRUMENT=$3

DIR="$(sed 's,/*[^/]\+/*$,,' <<< ${INSTRUMENT_DIR})" # Remove last folder from path

source ${KOHERON_SDK_PATH}/settings.sh
make -C ${KOHERON_SDK_PATH} NAME=${INSTRUMENT} INSTRUMENT_PATH=${DIR}
cp ${KOHERON_SDK_PATH}/tmp/${INSTRUMENT}-*.zip ${INSTRUMENT_DIR}