#!/bin/bash

set -e

MAKE_CMD=$1
KOHERON_SDK_PATH=$2
INSTRUMENT_DIR=$3
INSTRUMENT=$4

DIR="$(sed 's,/*[^/]\+/*$,,' <<< ${INSTRUMENT_DIR})" # Remove last folder from path

case "${MAKE_CMD}" in
    --build)
        source ${KOHERON_SDK_PATH}/settings.sh
        make -C ${KOHERON_SDK_PATH} NAME=${INSTRUMENT} INSTRUMENT_PATH=${DIR}
        cp ${KOHERON_SDK_PATH}/tmp/${INSTRUMENT}-*.zip ${INSTRUMENT_DIR}
        ;;
    --clean)
        make -C ${KOHERON_SDK_PATH} NAME=${INSTRUMENT} INSTRUMENT_PATH=${DIR} clean_instrument
        rm -f ${INSTRUMENT_DIR}/${INSTRUMENT}-*.zip
        ;;
    *)
        break
        ;;
esac