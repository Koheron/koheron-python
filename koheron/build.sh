#!/bin/bash

set -e

MAKE_CMD=$1
KOHERON_SDK_PATH=$2
INSTRUMENT_DIR=$3
INSTRUMENT=$4
HOST=$5

# DIR="$(sed 's,/*[^/]\+/*$,,' <<< ${INSTRUMENT_DIR})" # Remove last folder from path

case "${MAKE_CMD}" in
    --build)
        source ${KOHERON_SDK_PATH}/settings.sh
        make -C ${KOHERON_SDK_PATH} IPATH=${INSTRUMENT_DIR}
        cp ${KOHERON_SDK_PATH}/tmp/${INSTRUMENT}-*.zip ${INSTRUMENT_DIR}
        ;;
    --clean)
        make -C ${KOHERON_SDK_PATH} IPATH=${INSTRUMENT_DIR} clean_instrument
        rm -f ${INSTRUMENT_DIR}/${INSTRUMENT}-*.zip
        ;;
    --run)
        make -C ${KOHERON_SDK_PATH} IPATH=${INSTRUMENT_DIR} HOST=${HOST} run
        ;;
    *)
        echo "Invalid command ${MAKE_CMD}"
        ;;
esac