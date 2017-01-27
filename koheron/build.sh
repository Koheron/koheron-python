#!/bin/bash

set -e

MAKE_CMD=$1
INSTRUMENT_DIR=$2
INSTRUMENT=$3
HOST=$4

KOHERON_SDK_PATH=${INSTRUMENT_DIR}/tmp

# Install koheron-sdk in the instrument directory if not already there
if [ ! -d "${KOHERON_SDK_PATH}" ]; then
    koheron-sdk --path=${KOHERON_SDK_PATH} --version=develop install
fi

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