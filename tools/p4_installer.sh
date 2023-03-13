#!/usr/bin/env bash

run () {
    echo "$@"
    "$@" || exit 1
}

. /etc/os-release
echo "deb http://download.opensuse.org/repositories/home:/p4lang/xUbuntu_${VERSION_ID}/ /" | sudo tee /etc/apt/sources.list.d/home:p4lang.list
curl -fsSL "https://download.opensuse.org/repositories/home:p4lang/xUbuntu_${VERSION_ID}/Release.key" | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/home_p4lang.gpg > /dev/null
run sudo apt update
run sudo apt install -y p4lang-p4c
run sudo apt install -y p4lang-bmv2
