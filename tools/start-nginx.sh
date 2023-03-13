#!/usr/bin/env bash

num_vfs=4
nginx_root=/tmp/nginx
#script_dir=$(cd $(dirname $0);pwd)
script_dir=$(pwd)

usage() {
    echo
    echo "$0: usage"
    echo
    echo "  -n NUM	number of netnses, default $num_vfs"
    echo "  -h		print help"
    echo
}

while getopts n:h OPT
do
    case $OPT in
        n) num_vfs=$OPTARG ;;
        h) usage ; exit 1 ;;
        \?) usage ; exit 1 ;;
    esac
done


if [ -e $nginx_root ]; then
	sudo rm -r $nginx_root
fi
mkdir $nginx_root
echo "1234567890" > $nginx_root/10B.txt
dd if=/dev/zero of=$nginx_root/512k.img bs=1K count=512
dd if=/dev/zero of=$nginx_root/1m.img bs=1M count=1
dd if=/dev/zero of=$nginx_root/4m.img bs=1M count=4
dd if=/dev/zero of=$nginx_root/10m.img bs=1M count=10

sudo killall nginx
#for x in `seq 0 $(( $num_vfs - 1 ))`; do
for x in `seq 1 $(( $num_vfs - 0 ))`; do
	core=$(( ($x-1) * 2 + 1))
    echo allow 'Nginx Full' using ufw
    sudo ip netns exec ns$x ufw allow 'OpenSSH'
    sudo ip netns exec ns$x ufw allow 'Nginx Full'
    sudo ip netns exec ns$x ufw --force enable
	echo execute nginx on netns ns$x CPU core $core
	sudo ip netns exec ns$x taskset -c $core nginx -c $script_dir/nginx.conf
done

n=`ps ax|grep nginx | grep master | wc -l`
echo tried to execute $num_vfs nginx processes, and $n runs
