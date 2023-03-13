#!/usr/bin/env bash
p4c --target bmv2 --arch v1model --std p4-16 -o build.ecmper.bmv2 --p4runtime-files build.ecmper.bmv2/ecmper_bmv2.p4info.txt p4src/ecmper_bmv2.p4
