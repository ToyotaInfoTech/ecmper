#!/usr/bin/env python3

# ECMP-ER Router Controller For BMv2
# using P4Runtime API

import copy

import re
import ipaddress
from hashlib import md5
#from p4.v1 import p4runtime_pb2
from p4.config.v1 import p4info_pb2


# from flask import Flask, make_response, jsonify
from flask import Flask, make_response
app = Flask("c4bmv2-rest-api")

### Debug and Consistent Hash settings ------------------------------
global debugging
debugging = False

global use_chash
use_chash = False

def dprint(string):
    global debugging
    if debugging:
        print(string)

### BMv2 P4Runtime Shell Lib ----------------------------------------
import p4runtime_sh.shell as sh

class P4RuntimeBase(object):
    def __init__(self, p4info, p4bin):
        self.device_id = 1
        self.tables = dict()
        # self.mcgroup = McGroup()

        grpc_addr = 'localhost:9559'
        sh.setup(
            device_id=self.device_id,
            grpc_addr=grpc_addr,
            election_id=(0, 1), # (high, low)
            config=sh.FwdPipeConfig(p4info, p4bin)
        )

    def register_tables(self):
        t = TblIpv4Lpm("SwitchIngress.ecmper.ipv4_lpm")
        self.tables["ipv4_lpm"] = t
        t = TblCurNh("SwitchIngress.ecmper.cur_nh")
        self.tables["cur_nh"] = t
        t = TblPrvNh("SwitchIngress.ecmper.prv_nh")
        self.tables["prv_nh"] = t
        t = TblNeigh("SwitchIngress.ecmper.neigh")
        self.tables["neigh"] = t
        # Add more user defined tables here.

    def dump_tables(self, underline=False):
        s = ""
        for n in self.tables:
            # use dump() of each TblXXX class
            s += self.tables[n].dump(underline=True)
        return s

    def clear_table_entries(self, key=""):
        """ Delete all table entries. """
        def clear_table(key):
            name = self.tables[key].name
            print("  Clearing Table %s: %s" % (key, name))
            try:
                sh.TableEntry(name).read(lambda te: te.delete())
            except Exception as e:
                print("  > Error ignored while cleaning up (constant entry defined?)")
                print(e)

        if key != "":
            clear_table(key)
        else:
            print("Clear table entries")
            print("--------------------")
            for key in self.tables:
                clear_table(key)

    # def clear_mcgroup_entries(self):
    #     print("Clear Multicast Group entries")
    #     print("------------------------------")
    #     self.mcgroup.clear()

class TblBase(object):
    def __init__(self, name):
        self.name = name
        self.debug_pri_base = 2147483647 # DEBUG: priority not set as is via P4Runtime
    
    def add_entry(self, match_param, action, action_param, priority=0):
        te = sh.TableEntry(self.name)(action=action)
        for k in match_param:
            #print("add_entry: k {}: {}\n".format(k, match_param[k])) #DEBUG
            te.match[k] = str(match_param[k])
        for k in action_param:
            te.action[k] = str(action_param[k])
        # priority must be int for P4Runtime
        # te.priority = stoi(priority)
        if priority != 0:
            te.priority = self.debug_pri_base - stoi(priority) # DEBUG: priority not set as is via P4Runtime

        try:
            te.insert()
        except:
            # if entry with the same match params already exists
            te.modify()
    
    def del_entry(self, match_param, priority=0):
        te = sh.TableEntry(self.name)
        for k in match_param:
            te.match[k] = str(match_param[k])
        # te.priority = stoi(priority)
        if priority != 0:
            te.priority = self.debug_pri_base - stoi(priority) # DEBUG: priority not set as is via P4Runtime

        te.delete()

    def dump(self, underline=False):
        """ default dump() function called if not defined in each TblXXX class"""
        s = ""
        name = self.name
        if underline:
            s += ("-"*(len(name)+8)) + "\n"
            s += (" Table %s" % name ) + "\n"
            s += ("-"*(len(name)+8)) + "\n"
        else:
            s += ("| Table %s" % name ) + "\n"
        #sh.TableEntry(name).read(lambda te: print(te))
        tes = sh.TableEntry(name).read()
        for te in tes:
            s1 = te.__str__()
            s2 = re.sub(r"[\n\t]*", "", s1)
            s += re.sub(r"\s+", " ", s2) + "\n"
        return s

# name:ipv4_lpm, key: SwitchIngress.ipv4_lpm
class TblIpv4Lpm(TblBase):
    def get_match_param(self, ipv4prefix):
        mp = {}
        mp['dstAddr'] = ipv4prefix # x.x.x.x/n
        return mp

    def get_action_param(self, cur_nh_offset, cur_nh_count,
                               prv_nh_offset, prv_nh_count):
        ap = {}
        ap['cur_nh_offset'] = cur_nh_offset
        ap['cur_nh_count'] = cur_nh_count
        ap['prv_nh_offset'] = prv_nh_offset
        ap['prv_nh_count'] = prv_nh_count
        return ap

    def set_nh_index(self, **kwargs):
        action = 'set_nh_index'
        ipv4prefix_ = kwargs['dstaddr'] + "/" + str(kwargs['dstaddr_p_length'])
        mp = self.get_match_param(
            ipv4prefix = ipv4prefix_
        )
        ap = self.get_action_param(
            cur_nh_offset = kwargs['cur_nh_offset'],
            cur_nh_count = kwargs['cur_nh_count'],
            prv_nh_offset = kwargs['prv_nh_offset'],
            prv_nh_count = kwargs['prv_nh_count'],
        )
        self.add_entry(mp, action, ap)

    def dump(self, underline=False):
        s = ""
        name = self.name
        if underline:
            s += ("-"*(len(name)+8)) + "\n"
            s += (" Table %s" % name ) + "\n"
            s += ("-"*(len(name)+8)) + "\n"
        else:
            s += ("| Table %s" % name ) + "\n"
        tes = sh.TableEntry(name).read()
        num = 0
        for te in tes:
            num += 1
            s += ("%s | " % num)
            # Parse Match Fields
            mk = te.match._mk
            s += "match: "
            for m in mk:
                s += ("%s" % m)
                if m == "dstAddr":
                    s += (": %s" % ipaddress.IPv4Address(mk[m].lpm.value))
                    s += ("/%s"  % mk[m].lpm.prefix_len)
                else:
                    raise UserError("Unsupported match type for field\n")
            # Parse Actions
            a = te.action
            s += (" | action: %s(" % a.action_name.split(".")[-1])
            pvs = a._param_values
            for pv in pvs:
                if (pv == "cur_nh_offset" or pv == "cur_nh_count" or
                    pv == "prv_nh_offset" or pv == "prv_nh_count"
                ):
                    s += (" {}: {}".format(pv, int(pvs[pv].value.hex())))
            s += " )\n"
        return s

# name:prv_nh, key:SwitchIngress.ecmper.prv_nh
class TblPrvNh(TblBase):
    def get_match_param(self, nh_index):
        mp = {}
        mp['nh_index'] = nh_index
        return mp

    def get_action_param(self, nexthop):
        ap = {}
        ap['nexthop'] = nexthop # IPv4 addr
        return ap

    def set_nexthop(self, **kwargs):
        action = 'set_nexthop'
        mp = self.get_match_param(
            nh_index = kwargs['nh_index']
        )
        ap = self.get_action_param(
            nexthop = kwargs['nexthop']
        )
        self.add_entry(mp, action, ap)
    
    def set_drop(self, nh_index):
        action = 'drop'
        mp = self.get_match_param(nh_index)
        ap = {}
        self.add_entry(mp, action, ap)

    def dump(self, underline=False):
        s = ""
        name = self.name
        if underline:
            s += ("-"*(len(name)+8)) + "\n"
            s += (" Table %s" % name ) + "\n"
            s += ("-"*(len(name)+8)) + "\n"
        else:
            s += ("| Table %s" % name ) + "\n"
        tes = sh.TableEntry(name).read()
        num = 0
        for te in tes:
            num += 1
            s += ("%s | " % num)
            # Parse Match Fields
            mk = te.match._mk
            s += "match: "
            for m in mk:
                s += ("%s" % m)
                if m == "nh_index":
                    s += (": %s" % int.from_bytes(mk[m].exact.value, "big"))
                else:
                    raise UserError("Unsupported match type for field:\n{}")
            # Parse Actions
            a = te.action
            s += (" | action: %s(" % a.action_name.split(".")[-1])
            pvs = a._param_values
            for pv in pvs:
                if pv == "nexthop":
                    if len(pvs[pv].value) == 4:
                        s += (" {}: {}".format(pv, ipaddress.IPv4Address(pvs[pv].value)))
                    elif int(pvs[pv].value.hex()) == 0:
                        s += (" {}: 0.0.0.0".format(pv))
                    else:
                        s += (" {}: {}".format(pv, pvs[pv].value))
            s += " )\n"
        return s

# name:cur_nh, key:SwitchIngress.ecmper.cur_nh
class TblCurNh(TblBase):
    def get_match_param(self, nh_index):
        mp = {}
        mp['nh_index'] = nh_index
        return mp

    def get_action_param(self, nexthop):
        ap = {}
        ap['nexthop'] = nexthop # IPv4 addr
        return ap

    def set_nexthop(self, **kwargs):
        action = 'set_nexthop'
        mp = self.get_match_param(
            nh_index = kwargs['nh_index']
        )
        ap = self.get_action_param(
            nexthop = kwargs['nexthop']
        )
        self.add_entry(mp, action, ap)

    def set_drop(self, nh_index):
        action = 'drop'
        mp = self.get_match_param(nh_index)
        ap = {}
        self.add_entry(mp, action, ap)

    def dump(self, underline=False):
        s = ""
        name = self.name
        if underline:
            s += ("-"*(len(name)+8)) + "\n"
            s += (" Table %s" % name ) + "\n"
            s += ("-"*(len(name)+8)) + "\n"
        else:
            s += ("| Table %s" % name ) + "\n"
        tes = sh.TableEntry(name).read()
        num = 0
        for te in tes:
            num += 1
            s += ("%s | " % num)
            # Parse Match Fields
            mk = te.match._mk
            s += "match: "
            for m in mk:
                s += ("%s" % m)
                if m == "nh_index":
                    s += (": %s" % int.from_bytes(mk[m].exact.value, "big"))
                else:
                    raise UserError("Unsupported match type for field:\n{}")
            # Parse Actions
            a = te.action
            s += (" | action: %s(" % a.action_name.split(".")[-1])
            pvs = a._param_values
            for pv in pvs:
                if pv == "nexthop":
                    if len(pvs[pv].value) == 4:
                        s += (" {}: {}".format(pv, ipaddress.IPv4Address(pvs[pv].value)))
                    elif int(pvs[pv].value.hex()) == 0:
                        s += (" {}: 0.0.0.0".format(pv))
                    else:
                        s += (" {}: {}".format(pv, pvs[pv].value))
            s += " )\n"
        return s

# name:neigh, key:SwitchIngress.ecmper.neigh
class TblNeigh(TblBase):
    def get_match_param(self, nh_addr):
        mp = {}
        mp['nh_addr'] = nh_addr
        return mp

    def get_action_param(self, dstMac, port):
        ap = {}
        ap['dstMac'] = dstMac
        ap['port'] = port
        return ap

    def set_output(self, **kwargs):
        action = 'set_output'
        mp = self.get_match_param(
            nh_addr = kwargs['nh_addr']
        )
        ap = self.get_action_param(
            dstMac = kwargs['dstmac'],
            port = kwargs['port']
        )
        self.add_entry(mp, action, ap)

    def dump(self, underline=False):
        s = ""
        name = self.name
        if underline:
            s += ("-"*(len(name)+8)) + "\n"
            s += (" Table %s" % name ) + "\n"
            s += ("-"*(len(name)+8)) + "\n"
        else:
            s += ("| Table %s" % name ) + "\n"
        tes = sh.TableEntry(name).read()
        num = 0
        for te in tes:
            num += 1
            s += ("%s | " % num)
            # Parse Match Fields
            mk = te.match._mk
            s += "match: "
            for m in mk:
                s += ("%s" % m)
                if m == "nh_addr":
                    s += (": %s" % ipaddress.IPv4Address(mk[m].exact.value))
                else:
                    raise UserError("Unsupported match type for field\n")
            # Parse Actions
            a = te.action
            s += (" | action: %s(" % a.action_name.split(".")[-1])
            pvs = a._param_values
            for pv in pvs:
                if pv == "dstMac":
                    s += (" {}: {}".format(pv, pvs[pv].value.hex(":")))
                elif pv == "port":
                    s += (" {}: {}".format(pv, int.from_bytes(pvs[pv].value, "big")))
            s += " )\n"
        return s

### ECMP-ER specific Classes

# A simple consistent hash
# - https://gist.github.com/upa/b139cb05477d147f36af936604f84eea

class SimpleConsistentHash(object):
    def __init__(self, size, nvirtual):
        self.size = size # table size
        self.nvirtual = nvirtual # number of virtual nodes
        self.bucket = []
        self.nodes = []

    def add(self, node):
        if not node in self.nodes:
            self.nodes.append(node)
        
        
    def delete(self, node):
        if node in self.nodes:
            self.nodes.remove(node)

    def lookup(self, value, hash_func = None):

        if len(self.bucket) < self.size:
            raise RuntimeError("bucket len (%d) is smaller than size (%d)" %
                               (len(self.bucket), self.size))

        if not hash_func:
            hash_func = lambda x: int(md5(str(x).encode()).hexdigest(), 16)
        h = hash_func(value) % self.size

        return self.bucket[h]
            

    def populate(self):

        if self.size < len(self.nodes):
            raise ValueError("too many nodes %d > table size %d" %
                             (len(self.nodes), self.size))

        hash_to_node = {} # key hash: value node
        hnodes = [] # hash of nodes including virtual nodes
        nhnodes = self.nvirtual # number of hash nodes including virtual

        while nhnodes < len(self.nodes):
            nhnodes += 1
         
        # create 'nhnodes' hash values for virtual nodes between 0 - self.size
        while nhnodes != len(hnodes):
            for node in self.nodes:

                h = int(md5(str(node).encode()).hexdigest(), 16)
                v = h % self.size

                while v in hash_to_node:
                    h = int(md5(str(h).encode()).hexdigest(), 16)
                    v = h % self.size
                hash_to_node[v] = node
                hnodes.append(v)

                if nhnodes == len(hnodes):
                    break

        hnodes.sort()
                
        # populate bucket
        bucket = []
        for hnode in hnodes:
            while len(bucket) < hnode:
                bucket.append(hash_to_node[hnode])

        while len(bucket) < self.size:
            bucket.append(hash_to_node[hnodes[0]])

        self.bucket = bucket
        
        return

    def dump(self):
        print(self.bucket)

def install_nh_drop_entry():
    dprint("install drop() entry to index 0 on cur and prv NHs");
    p4rtb.tables["prv_nh"].set_drop("0")
    p4rtb.tables["cur_nh"].set_drop("0")

def add_entry(table, **kwargs):
    dprint("Add To {}: {}".format(table, kwargs))
    if table == "ipv4_lpm":
        p4rtb.tables[table].set_nh_index(**kwargs)
    elif table == "cur_nh":
        p4rtb.tables[table].set_nexthop(**kwargs)
    elif table == "prv_nh":
        p4rtb.tables[table].set_nexthop(**kwargs)
    elif table == "neigh":
        p4rtb.tables[table].set_output(**kwargs)
    else:
        raise Exception("invalid table '{}'".format(table))


class Route(object):
    def __init__(self, prefix, preflen, nexthop):
        self.prefix = prefix
        self.preflen = preflen
        self.nexthop = nexthop
        # nexthop "connected" means connected route 

    def __eq__(self, other):
        if (self.prefix == other.prefix and
            self.preflen == other.preflen and
            self.nexthop == other.nexthop):
            return True
        return False

    def __ne__(self, ther):
        return not self.__eq__(other)

    def __lt__(self, other):
        # This is very skimped work. should compare as IP address
        return ("{}/{}".format(self.prefix, self.preflen) <
                "{}/{}".format(other.prefix, other.preflen))
    
    def __gt__(self, other):
        # This is very skimped work. should compare as IP address
        return ("{}/{}".format(self.prefix, self.preflen) >
                "{}/{}".format(other.prefix, other.preflen))

    def __str__(self):
        return "<{}/{} to {}>".format(self.prefix, self.preflen, self.nexthop)


class ECMPerLpmEntry(object):
    def __init__(self, prefix, preflen):
        self.prefix = prefix
        self.preflen = preflen

        self.prv_count = 0
        self.prv_offset = 0
        self.prv_nh = [] # list of nexthop

        self.cur_count = 0
        self.cur_offset = 0
        self.cur_nh = [] # list of nexthop

    def __eq__(self, other):
        if (self.prefix == other.prefix and
            self.preflen == other.preflen and
            self.prv_count == other.prv_count and
            self.prv_offset == other.prv_offset and
            self.cur_count == other.cur_count and
            self.cur_offset == other.cur_offset):
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def append_cur_nexthop(self, nexthop):
        self.cur_nh.append(nexthop)

    def append_prv_nexthop(self, nexthop):
        self.prv_nh.append(nexthop)

    def _expand_nh(self, nh):
        # nh is self.cur_nh or self.prv_nh

        """
        The number of Nexthop entries for a LPM route must be
        power of 2. So, this function expands Nexthop entries
        to fit the minimum power of 2 that is equal to or
        grater than the number of Nexthop entries.

        XXX: this can be a consistent hashing
        """

        n = len(nh)
        if n == 0:
            # len 0 means this LPMEntry has only prv or cur nh table.
            return nh

        m = 1
        if n > 1 :
            # this is ECMP route
            while m < n:
                m <<= 1
            m <<= 2

        # Ok, we need 'm' nexthop entries
        expanded_nh = []
        for x in range(m):
            expanded_nh.append(nh[x % n])
        return expanded_nh

    def _expand_nh_with_chash(self, nh):
        n = len(nh)
        if n == 0 or n == 1:
            # len 0 means this LPMEntry has only prv or cur nh table.
            # len 1 means it is not ECMP route
            return nh

        # this is ECMP route
        m = 256
        while m < n:
            m <<= 1

        # Ok, we need 'm' nexthop entries
        nvirtual = int(m * 0.95)
        ch = SimpleConsistentHash(m, nvirtual)
        for n in nh:
            ch.add(n)
        ch.populate()
        return ch.bucket

    def expand_cur_nh(self):
        global use_chash
        if use_chash:
            self.cur_nh = self._expand_nh_with_chash(self.cur_nh)
        else:
            self.cur_nh = self._expand_nh(self.cur_nh)

    def expand_prv_nh(self):
        global use_chash
        if use_chash:
            self.prv_nh = self._expand_nh_with_chash(self.prv_nh)
        else:
            self.prv_nh = self._expand_nh(self.prv_nh)


class ECMPerTable(object):
    def __init__(self):
        self.lpm = {} # key is (prefix, preflen)

        self.prv_nh = [] # filled after do_encode(). list of Nexthop
        self.cur_nh = [] # filled after do_encode(). list of Nexthop

    def dump(self):
        # for debug
        print("")
        print("=================================================")
        print("prv_nh")
        cnt = 0
        for nexthop in self.prv_nh:
            print("%4d: %s" % (cnt, nexthop))
            cnt += 1
            
        print("cur_nh")
        cnt = 0
        for nexthop in self.cur_nh:
            print("%4d: %s" % (cnt, nexthop))
            cnt += 1

        print("lpm table")
        for (prefix, preflen) in sorted(self.lpm.keys()):
            e = self.lpm[(prefix, preflen)]
            print("%s/%d cur_off %d cur_cnt %d prv_off %d prv_cnt %d" %
                  (prefix, preflen,
                   e.cur_offset, e.cur_count, e.prv_offset, e.prv_count))

        print("=================================================")
        print("")

    def _find_lpm_entry(self, prefix, preflen):
        if not (prefix, preflen) in self.lpm:
            # create and add entry to lpm table (self.lpm) if lookup failed
            entry = ECMPerLpmEntry(prefix, preflen)
            self.lpm[(prefix, preflen)] = entry
        else:
            entry = self.lpm[(prefix, preflen)]
        return entry
            
    def add_route_to_cur(self, route):
        if not isinstance(route, Route):
            raise RuntimeError("invalid type: {}".format(route))

        lpm_entry = self._find_lpm_entry(route.prefix, route.preflen)
        lpm_entry.append_cur_nexthop(route.nexthop)
        
    def add_route_to_prv(self, route):
        if not isinstance(route, Route):
            raise RuntimeError("invalid type: {}".format(route))

        lpm_entry = self._find_lpm_entry(route.prefix, route.preflen)
        lpm_entry.append_prv_nexthop(route.nexthop)

    def do_encode(self):
        """
        Calculate NH entries on this ECMPerTable object.
        We need to care about the ECMP ER NH structure:

        * LPM Table
        | Destination |   Previous    |    Current    |
        +-------------+---------------+---------------+
        | Prefix/Len -> offset, count | offset, count |
        | Prefix/Len -> offset, count | offset, count |

                                  count must be power of 2

        * Nexthop Table
        | Index |     Nexthop Address      |
        +-------+--------------------------+
        |   0   |          DROP            | <= offset 0, count 1 means drop
        |   1   |       192.168.0.1        |
        |   2   |       192.168.0.2        |
        |   3   |         0.0.0.0          | <= 0.0.0.0 means connected route
        
        There is still very large room for optimization to minimize 
        resource usage of the NH tables.
        """

        prv_nh = [ "drop" ] # a list of joined all prv nexthops
        prv_index = 1 # 0 is drop()

        cur_nh = [ "drop" ] # a list of joined all cur nexthops
        cur_index = 1 # 0 is drop()

        for (prefix, preflen) in sorted(self.lpm.keys()):

            lpm_entry = self.lpm[(prefix, preflen)]

            lpm_entry.expand_prv_nh()
            lpm_entry.prv_offset = prv_index
            lpm_entry.prv_count = len(lpm_entry.prv_nh)
            prv_index += lpm_entry.prv_count # advance index
            prv_nh += lpm_entry.prv_nh # add nexthops to a single list

            lpm_entry.expand_cur_nh()
            lpm_entry.cur_offset = cur_index
            lpm_entry.cur_count = len(lpm_entry.cur_nh)
            cur_index += lpm_entry.cur_count
            cur_nh += lpm_entry.cur_nh

        self.prv_nh = prv_nh
        self.cur_nh = cur_nh

    def do_install(self):
        for index in range(1, len(self.prv_nh)): # skip index 0 is drop()
            nexthop = self.prv_nh[index]
            if nexthop == "connected":
                nexthop = "0.0.0.0"
            add_entry("prv_nh", nh_index = index, nexthop = nexthop)

        for index in range(1, len(self.cur_nh)): # skip index 0 is drop()
            nexthop = self.cur_nh[index]
            if nexthop == "connected":
                nexthop = "0.0.0.0"
            add_entry("cur_nh", nh_index = index, nexthop = nexthop)

        for (prefix, preflen) in self.lpm.keys():
            entry = self.lpm[(prefix, preflen)]
            add_entry("ipv4_lpm",
                      dstaddr = prefix, dstaddr_p_length = preflen,
                      cur_nh_offset = entry.cur_offset,
                      cur_nh_count = entry.cur_count,
                      prv_nh_offset = entry.prv_offset,
                      prv_nh_count = entry.prv_count)
        
        #print(p4rtb.dump_tables(underline=True)) # DEBUG

    def do_clear(self):
        # clear Table SwitchIngress.ecmper.prv_nh, cur_nh
        p4rtb.clear_table_entries("ipv4_lpm")
        p4rtb.clear_table_entries("prv_nh")
        p4rtb.clear_table_entries("cur_nh")


class NextHopInstaller(object):
    def __init__(self):
        self.add_queue = [] # Route objects to be processed
        self.del_queue = [] # Route objects to be processed
        """
        NextHopInstaller stores Route objects appended via the REST API
        (/add or /del). 

        when /install is kicked, it start to encode RIB to NH and
        install the both tables to the switch.
        """
        self.cur_routes = [] # Route objects for current NH
        self.prv_routes = [] # Route objects for previous NH

    def _queue_append(self, queue, route):
        if not isinstance(route, Route):
            print("{} is not Route object".format(route))
            return False
        if route in queue:
            print("{} is already exist in the queue".format(route))
            return False
        queue.append(route)
        return True

    def add_queue_append(self, route):
        return self._queue_append(self.add_queue, route)

    def del_queue_append(self, route):
        return self._queue_append(self.del_queue, route)


    def process_routes(self):

        """
        Start to process queued Route objects. 

        Move cur to prv, and process add_queue and del_queue
        for the cur_routes, and calculate the previous NH
        and current NH from prv_routes and cur_routes, respectively.
        """

        # Update prev and current route objects
        self.prv_routes = copy.copy(self.cur_routes)

        for route in self.add_queue:
            if not route in self.cur_routes:
                self.cur_routes.append(route)
            
        for route in self.del_queue:
            if route in self.cur_routes:
                self.cur_routes.remove(route)

        # Create ECMPerTable from the route objects.
        table = ECMPerTable()

        for route in self.prv_routes:
            table.add_route_to_prv(route)

        for route in self.cur_routes:
            table.add_route_to_cur(route)

        # Encode LPM table and NH entries on the ECMPerTable object
        table.do_encode()
            
        # just debug
        #global debugging
        if debugging:
            table.dump()

        if debugging:
            return # debug mode

        """
        1. clear table prv_nh, cur_nh, ipv4_lpm
        2. install drop() entry to index 0 on cur and prv NHs
        3. install entries to table prv_nh, cur_nh, ipv4_lpm
        XXX: we should update partially...  not clear and install
        """
        # install
        table.do_clear()
        install_nh_drop_entry()
        table.do_install()
        
        # revoke add/del queues
        self.add_queue = []
        self.del_queue = []

    def neigh_add(self, nh_addr, port, dstmac):
        args = { "nh_addr" : nh_addr, "dstmac" : dstmac, "port" : port}
        print("add neighbor {}".format(args))
        p4rtb.tables["neigh"].set_output(**args)

    def neigh_del(self, nh_addr):
        t = p4rtb.tables["neigh"]
        mp = t.get_match_param(nh_addr)
        print("del neighbor {}".format(mp))
        t.del_entry(mp)

    def table_all_clear(self):
        p4rtb.clear_table_entries()

nh_installer = None

### REST API ---------------------------------------------------------
""" REST API """

def rest_add_or_del_route(cmd, prefix, preflen, nexthop):
    global nh_installer
    
    route = Route(prefix, preflen, nexthop)
    if cmd == "add":
        ret = nh_installer.add_queue_append(route)        
    elif cmd == "del":
        ret = nh_installer.del_queue_append(route)

    res = make_response()

    if not ret:
        res.data = "invalid route"
        res.status_code = 400
        print("{} {} failed".format(cmd, route))
    else:
        res.data = "Route: {}/{} to {} enqueued".format(prefix, preflen,
                                                        nexthop)
        res.status_code = 200
        print("{} {} success".format(cmd, route))

    return res

@app.route("/add/<prefix>/<int:preflen>/<nexthop>", methods = ["PUT"])
def rest_add_route(prefix, preflen, nexthop):
    res = make_response()
    try:
        res = rest_add_or_del_route("add", prefix, preflen, nexthop)
    except Exception as e:
        print("rest_add_route failed: {}".format(e))
        res.status_code = 500
    return res

@app.route("/del/<prefix>/<int:preflen>/<nexthop>",  methods = ["PUT"])
def rest_del_route(prefix, preflen, nexthop):
    res = make_response()
    try:
        res = rest_add_or_del_route("del", prefix, preflen, nexthop)
    except Exception as e:
        print("rest_add_route failed: {}".format(e))
        res.status_code = 500
    return res


@app.route("/install", methods = ["PUT"])
def rest_install():
    global nh_installer

    res = make_response()

    try:
        nh_installer.process_routes()
        res.status_code = 200
    except Exception as e:
        res.status_code = 500
        print("install failed: {}".format(e))

    return res


@app.route("/neigh/add/<nh_addr>/<int:port>/<dstmac>", methods = ["PUT"])
def rest_neigh_add(nh_addr, port, dstmac):
    global nh_installer

    res = make_response()

    try:
        nh_installer.neigh_add(nh_addr, port, dstmac)
        res.status_code = 200
    except Exception as e:
        res.status_code = 500
        print("neighbor add failed: {}".format(e))

    return res


@app.route("/neigh/del/<nh_addr>", methods = ["PUT"])
def rest_neigh_del(nh_addr):
    global nh_installer

    res = make_response()

    try:
        nh_installer.neigh_del(nh_addr)
        res.status_code = 200
    except Exception as e:
        res.status_code = 500
        print("neighbor del failed: {}".format(e))

    return res

@app.route("/clear", methods = ["PUT"])
def rest_clear():
    global nh_installer

    res = make_response()

    try:
        # clear all tables and add drop entry for cur_nh, prv_nh
        nh_installer.table_all_clear()
        install_nh_drop_entry()
        res.status_code = 200
    except Exception as e:
        res.status_code = 500
        print("clear all table failed: {}".format(e))

    # recreate nh_installer
    nh_installer = NextHopInstaller()

    return res

@app.route("/tables", methods = ["GET"])
def get_tables():
    res = make_response()
    # Note: In Python3, there is no implicit cast from str to bytes, so use encode()
    res.data += p4rtb.dump_tables(underline=True).encode('utf-8')
    res.status_code = 200
    return res

@app.route("/tables/<path_string>", methods = ["GET"])
def get_tables_path(path_string):
    res = make_response()
    res.status_code = 200
    res.data += p4rtb.tables[path_string].dump().encode('utf-8')
    return res

def run(addr):
    app.run(host = addr, debug = None)

### MAIN -------------------------------------------------------------
def main(p4info = None, p4bin = None, addr = None, chash = False, enable_debug = False):
    global debugging
    global use_chash

    if not p4info:
        p4info =  "../build.ecmper.bmv2/ecmper_bmv2.p4info.txt"
    if not p4bin:
        p4bin  = "../build.ecmper.bmv2/ecmper_bmv2.json"
    if not addr:
        addr = "0.0.0.0"
    if enable_debug:
        debugging = True
    if chash:
        use_chash = True

    # instantiate nh installer
    global nh_installer
    nh_installer = NextHopInstaller()

    # Connect to P4SW via P4Runtime and init tables.
    print("Connecting to ECMP-ER Router (bmv2) via P4Runtime.")
    print("!!! Exit by entering CTRL+\\ !!!")
    print("--------------------------------------------------")

    # instantiate P4Runtime Base Object
    global p4rtb
    p4rtb = P4RuntimeBase(p4info, p4bin)
    p4rtb.register_tables()
    #print(p4rtb.dump_tables(underline=True)) # DEBUG

    if not debugging:
        install_nh_drop_entry()
        run(addr)
    else:
        print("DEBUG: running in debugging mode")
        install_nh_drop_entry()
        run(addr)

if __name__ == "__main__":
    #main(addr = "0.0.0.0", enable_debug=True)
    main(addr = "0.0.0.0")
