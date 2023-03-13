#!/bin/bash -eu

script_dir=$(cd $(dirname $0);pwd)
xdp=$script_dir/../xdp/redirect.o
num_vfs=4
action="attach"
foption=""

usage() {
    echo
    echo "$0: usage"
    echo
    echo "  -n NUM	number of netnses, default $num_vfs"
    echo "  -a           attach xdp program (default)"
    echo "  -d           detach xdp program"
    echo "  -f           force attach (override prior attached program)"
    echo "  -x XDPOBJ    xdp obj to be attached, default $xdp "
	echo
}

while getopts n:adfx:h OPT
do
    case $OPT in
        n) num_vfs=$OPTARG ;;
        a) action="attach" ;;
        d) action="detach" ;;
        f) foption="-force" ;;
        x) xdp=$OPTARG ;;
        h) usage ; exit 1 ;;
        \?) usage ; exit 1 ;;
    esac
done

if [ ! -e $xdp ]; then
        echo $xdp does not exit
        exit 1
fi

for ns in `seq 1 $(( $num_vfs ))`; do
	
    ipns="sudo ip netns exec ns$ns"

	if [ "$action" = "attach" ]; then
	 	#$ipns ip $foption link set dev veth$ns xdp object $xdp section xdp_prog
        # BUG: use xdpgeneric ... xdp would not process redirecting TCP correctly
        $ipns ip link set dev veth$ns xdp off
	 	$ipns ip $foption link set dev veth$ns xdpgeneric object $xdp section xdp_prog
	fi

	if [ "$action" = "detach" ]; then
		$ipns ip link set dev veth$ns xdp off
		$ipns ip link set dev veth$ns xdpgeneric off
	fi
done
