#!/usr/bin/env bash

# This script will create(remove) veth and namespace

# XDP has MTU limitation which is differnet per driver
#MAX_MTU=10240
MAX_MTU=3498

if [[ $(id -u) -ne 0 ]] ; then echo "Please run with sudo" ; exit 1 ; fi

# disable -e to keep the script running to clean up while after partially failed
#set -e

if [ -n "$SUDO_UID" ]; then
    uid=$SUDO_UID
else
    uid=$UID
fi

run () {
    echo "$@"
    "$@"
    #"$@" || exit 1
}

silent () {
    "$@" 2> /dev/null || true
}

create_netns_vethpairs () {
    echo "create_netns $NUM"
    for ((num=1; num<($NUM+1); num++))
    do
	    num_host=$((num))
        HOST="ns$num_host"
        num_veth=$((num))
        VETH="veth$num_veth"
        VETH_P4SW="veth$((num_veth+100))"
        echo "creating $HOST $VETH 10.0.0.$num_host/24 db8::$num_host/64"
        # Create veth pairs
        if ! ip link show $VETH &> /dev/null; then
            run ip link add name $VETH type veth peer name $VETH_P4SW
        fi
        run ip link set dev $VETH_P4SW mtu $MAX_MTU up
        
        # Create network namespaces
        run ip netns add $HOST
        # Assign veth to the host
        run ip link set $VETH netns $HOST
        run ip netns exec $HOST ip link set $VETH address 02:03:04:05:06:$num_host
        run ip netns exec $HOST ip addr add 10.0.0.$((num_host))/24 dev $VETH
        run ip netns exec $HOST ip -6 addr add db8::$num_host/64 dev $VETH
        # Assign VIP (nginx) address
        run ip netns exec $HOST ip addr add 10.0.10.0/32 dev lo
        # Link up loopback/veth
        run ip netns exec $HOST ip link set dev $VETH mtu $MAX_MTU up
        run ip netns exec $HOST ifconfig lo up
        # Trun OFF checksum offload on $HOST $VETH
        # ip netns exec ns1 ethtool --show-offload veth1
        run ip netns exec $HOST ethtool --offload $VETH rx off tx off
    done
}

create_ns99_vethpairs () {
    NETNS_NAME="ns99"
    VETH_NAME="veth99"
    echo "creating $NETNS_NAME $VETH_NAME 10.0.1.99/64 db8:1::99/64"
    run ip link add name $VETH_NAME type veth peer name veth100
    run ip netns add $NETNS_NAME
    run ip link set $VETH_NAME netns $NETNS_NAME
    run ip netns exec $NETNS_NAME ip link set $VETH_NAME address 02:03:04:05:06:99
    run ip netns exec $NETNS_NAME ip addr add 10.0.1.99/24 dev $VETH_NAME
    run ip netns exec $NETNS_NAME ip -6 addr add db8:1::99/64 dev $VETH_NAME
    # Link up loopback/veth
    run ip netns exec $NETNS_NAME ip link set dev $VETH_NAME mtu $MAX_MTU up
    run ip link set dev veth100 mtu $MAX_MTU up
    # Trun OFF checksum offload on $HOST $VETH
    # ip netns exec ns1 ethtool --show-offload veth1
    run ip netns exec $NETNS_NAME ethtool --offload $VETH_NAME rx off tx off
}

destroy_netns_vethpairs () {
    echo "destroy_network $NUM"
    for ((num=1; num<($NUM+1); num++))
    do
        num_host=$((num))
        HOST="ns$num_host"
        run ip link del veth$(($num+100))
        run ip netns del $HOST
    done
}

destroy_ns99_vethpairs (){
    echo "destroy ns99 and veth pair"
    run ip link del veth100
    run ip netns del ns99
}

while getopts "c:d:" ARGS;
do
    case $ARGS in
    c )
        NUM=$OPTARG
        create_ns99_vethpairs
        create_netns_vethpairs
        exit 1;;
    d )
        NUM=$OPTARG
        destroy_ns99_vethpairs
        destroy_netns_vethpairs
        exit 1;;
    esac
done

cat << EOF
usage: sudo ./$(basename $BASH_SOURCE) <option>
option:
    -c <num> : create_netns with <num> hosts and assign address
    -d <num> : destroy_netns with <num> hosts
EOF
