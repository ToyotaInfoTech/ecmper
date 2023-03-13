#!/usr/bin/env bash

# install route entries to ECMP-ER Router (bmv2)

rip_base="10.0.0"
vip="10.0.10.0"

run () {
    echo "$@"
    "$@" || exit 1
}

silent () {
    "$@" 2> /dev/null || true
}

usage() {
    echo
    echo "add/del routes to ECMP-ER Router via HTTP API"
    echo "Virtual IP: $vip, Real IP: $rip_base.X"
    echo
#    echo "  -n NUM    number of servers"
    echo "  -s NUM    server id (start)"
    echo "  -e NUM    server id (end)"
    echo "  -i SEC    interval between adding/deleting server"
    echo "  -d debug log (e.g. show tables each time"
    echo "  -h help"
    echo
}

while getopts n:i:s:e:hd OPT
do
    case $OPT in
#        n) num=$OPTARG ;;
        s) sid=$OPTARG ;;
        e) eid=$OPTARG ;;
        i) interval=$OPTARG ;;
        d) debug="yes" ;;
        h) usage ; exit 1 ;;
        \?) usage ; exit 1 ;;
    esac
done

echo "DEBUG: num=$num, interval=$interval"

#for n in `seq 1 $num`; do
for ((i=$sid; i<=$eid; i++))
do
    # VIP
    # @app.route("/add/<prefix>/<int:preflen>/<nexthop>", methods = ["PUT"])
    run http PUT localhost:5000/add/$vip/32/$rip_base.$i
    http PUT localhost:5000/install
    if [[ $debug == "yes" ]]; then
        http localhost:5000/tables
    fi
    sleep $interval
done

#for n in `seq 0 $(($num - 1))`; do
for ((i=$eid; i>=$sid; i--))
do
    run http PUT localhost:5000/del/$vip/32/$rip_base.$i
    http PUT localhost:5000/install
    if [[ $debug == "yes" ]]; then
        http localhost:5000/tables
    fi
    sleep $interval
done


exit 1

# VIP
# @app.route("/add/<prefix>/<int:preflen>/<nexthop>", methods = ["PUT"])
http PUT localhost:5000/add/10.0.10.0/32/10.0.0.1
http PUT localhost:5000/add/10.0.10.0/32/10.0.0.2
http PUT localhost:5000/add/10.0.10.0/32/10.0.0.3
http PUT localhost:5000/add/10.0.10.0/32/10.0.0.4

# Client
# http PUT localhost:5000/add/10.0.1.0/24/connected
# http PUT localhost:5000/del/10.0.1.0/24/connected

# Install Route Entries
http PUT localhost:5000/install

# Show table entries
http localhost:5000/tables
