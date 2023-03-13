#!/usr/bin/env bash

usage() {
    echo
    echo "$0: usage"
    echo
    echo "  -d : run in debug mode"
    echo "  -h : print help"
    echo
}

while getopts dh OPT
do
    case $OPT in
        d) mode="debug" ;;
        h) usage ; exit 1;;
        \?) usage ; exit 1;;
    esac
done

if [[ $mode == "debug" ]]; then
    sudo simple_switch_grpc --log-console --device-id 1 \
    -i 0@veth100 -i 1@veth101 -i 2@veth102 -i 3@veth103 -i 4@veth104 \
    ../build.ecmper.bmv2/ecmper_bmv2.json
else
    sudo simple_switch_grpc --device-id 1 \
    -i 0@veth100 -i 1@veth101 -i 2@veth102 -i 3@veth103 -i 4@veth104 \
    ../build.ecmper.bmv2/ecmper_bmv2.json
fi
