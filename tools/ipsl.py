#!/usr/bin/env python3

# This "ipsl" is a tool written by Ryo Nakamura: https://gist.github.com/upa
# This file was downloaded from below gist (upa/ipsl)
# https://gist.github.com/upa/a7ddce981c734c8cf0e5d12a3722c5f2

import sys
import time
import json
import argparse
import subprocess

class Counter:
    def __init__(self, stats64_json = None ):
        self.byte = 0
        self.packet = 0
        self.error = 0
        self.dropped = 0
        self.over_error = 0
        self.multicast = 0

        if stats64_json:
            self.import_stats64_json(stats64_json)
            
    def import_stats_json(self, j):
        if "bytes"in j:
            self.byte = j["bytes"]
        if "tx_bytes" in j:
            self.byte = j["tx_bytes"]
        if "packets" in j:
            self.packet = j["packets"]
        if "tx_packets" in j:
            self.packet = j["tx_packets"]
        if "errors" in j:
            self.error = j["errors"]
        if "over_errors" in j:
            self.over_error = j["over_errors"]
        if "multicsat" in j:
            self.multicast = j["multicsat"]

    def copy_from_counter(self, other):
        self.byte = other.byte
        self.packet = other.packet
        self.error = other.error
        self.over_error = other.over_error
        self.multicast = other.multicast

class Interface:
    def __init__(self, ifname, lower_up = False):
        self.ifname = ifname
        self.tx_now = Counter()
        self.tx_old = Counter()
        self.rx_now = Counter()
        self.rx_old = Counter()
        self.time_new = time.time()
        self.time_old = time.time() - 1
        self.lower_up = lower_up

    def update(self, timestamp, iface_json):
        if "stats64" in iface_json:
            stats_json = iface_json["stats64"]
        else:
            stats_json = iface_json["stats"]
        self.tx_old.copy_from_counter(self.tx_now)
        self.rx_old.copy_from_counter(self.rx_now)
        self.tx_now.import_stats_json(stats_json["tx"])
        self.rx_now.import_stats_json(stats_json["rx"])

        self.time_old = self.time_new
        self.time_new = timestamp
    
    def rate_to_dict(self):
        elapsed = self.time_new - self.time_old
        tx_bps = (self.tx_now.byte - self.tx_old.byte) * 8 / elapsed
        tx_pps = (self.tx_now.packet - self.tx_old.packet) / elapsed
        rx_bps = (self.rx_now.byte - self.rx_old.byte) * 8 / elapsed
        rx_pps = (self.rx_now.packet - self.rx_old.packet) / elapsed
        return { "tx_bps" : tx_bps, "tx_pps" : tx_pps,
                 "rx_bps" : rx_bps, "rx_pps" : rx_pps,
                 "ifname" : self.ifname,
        }

    def print_rate_line(self, roundup = False, txonly = False, rxonly = False):
        d = self.rate_to_dict()

        def _roundup(rate, do):
            unit = ""
            if not do:
                return rate, unit

            if rate > 1000:
                rate /= 1000
                unit = "K"
            if rate > 1000:
                rate /= 1000
                unit = "M"
            if rate > 1000:
                rate /= 1000
                unit = "G"
            return rate, unit

        tx_bps, tx_bps_unit = _roundup(d["tx_bps"], roundup)
        tx_pps, tx_pps_unit = _roundup(d["tx_pps"], roundup)
        rx_bps, rx_bps_unit = _roundup(d["rx_bps"], roundup)
        rx_pps, rx_pps_unit = _roundup(d["rx_pps"], roundup)

        if not rxonly:
            print("{:<12} tx {:.2f} {}bps {:.2f} {}pps".format(self.ifname,
                                                               tx_bps,
                                                               tx_bps_unit,
                                                               tx_pps,
                                                               tx_pps_unit))
        if not txonly:
            print("{:<12} rx {:.2f} {}bps {:.2f} {}pps".format(self.ifname,
                                                               rx_bps,
                                                               rx_bps_unit,
                                                               rx_pps,
                                                               rx_pps_unit))


def do_ipsl():
    return json.loads(subprocess.check_output(["ip", "-s", "-j", "link"]))

def retrieve_iflist():

    ipsl_json = do_ipsl()

    iflist = {} # key is ifname, value is class Interface

    for iface_json in ipsl_json:
        iface = Interface(iface_json["ifname"])
        iflist[iface_json["ifname"]] = iface

        if "vfinfo_list" in iface_json:
            for vfinfo_json in iface_json["vfinfo_list"]:
                vfname = "{}v{}".format(iface_json["ifname"],
                                        vfinfo_json["vf"])
                vf = Interface(vfname)
                iflist[vfname] = vf
    
    return iflist

def update_with_ipsl_json(iflist, timestamp, ipsl_json):

    for iface_json in ipsl_json:
        iface = iflist[iface_json["ifname"]]
        iface.update(timestamp, iface_json)

        if "vfinfo_list" in iface_json:
            for vfinfo_json in iface_json["vfinfo_list"]:
                vfname = "{}v{}".format(iface_json["ifname"],
                                        vfinfo_json["vf"])
                vf = iflist[vfname]
                vf.update(timestamp, vfinfo_json)

def ipsl(args):

    # retrive interface list including VF
    iflist = retrieve_iflist()

    while True:
        before = time.time()
        before_json = do_ipsl()
        time.sleep(args.interval)
        after = time.time()
        after_json = do_ipsl()

        update_with_ipsl_json(iflist, before, before_json)
        update_with_ipsl_json(iflist, after, after_json)

        print("========================================")
        for ifname in sorted(iflist.keys()):
            if args.ifnamegrep:
                if not args.ifnamegrep in ifname:
                    continue
            iface = iflist[ifname]
            iface.print_rate_line(roundup = not args.noroundup,
                                  txonly = args.tx,
                                  rxonly = args.rx)
        sys.stdout.flush()
            
        if args.timeout:
            args.timeout -= args.interval
            if args.timeout <= 0:
                break

        
    
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interval", type = float, default = 1.0,
                        help = "interval")
    parser.add_argument("-n", "--noroundup", action = "store_true",
                        default = False,
                        help = "not round up unit")
    parser.add_argument("-g", "--ifnamegrep", default = False,
                        help = "grep string for interface name")
    parser.add_argument("--tx", action = "store_true", default = False,
                        help = "print tx only")
    parser.add_argument("--rx", action = "store_true", default = False,
                        help = "print rx only")
    parser.add_argument("-t", "--timeout", type = float, default = 0.0,
                        help = "timeout")

    args = parser.parse_args()

    ipsl(args)

if __name__ == "__main__":
    main()
