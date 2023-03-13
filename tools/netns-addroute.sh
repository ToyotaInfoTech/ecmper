#!/usr/bin/env bash

run () {
    echo "$@"
    "$@"
    #"$@" || exit 1
}

num_vfs=4
router_mac="02:00:00:00:00:01"

for x in `seq 1 $(( $num_vfs - 0 ))`; do
    run sudo ip netns exec ns$x ip route add 0.0.0.0/0 via 10.0.0.100
    run sudo ip netns exec ns$x ip neigh add 10.0.0.100 dev veth$x lladdr $router_mac
done

run sudo ip netns exec ns99 ip route add 0.0.0.0/0 via 10.0.1.100
run sudo ip netns exec ns99 ip neigh add 10.0.1.100 dev veth99 lladdr $router_mac
