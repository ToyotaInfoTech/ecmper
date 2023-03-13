/*
 * Copyright 2022 Toyota Motor Corporation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Kentaro Ebisawa <ebisawa@toyota-tokyo.tech>
 *
 */


/* ingress processing */
control ECMPER(
        inout headers_t hdr,
        inout ingress_metadata_t ig_md,
        inout PortId_t egress_port
//        inout bit<3> drop_ctl // ingress_intrinsic_metadata_for_deparser_t
    ){

#ifdef ECMPER_TNA
    Hash<bit<16>>(HashAlgorithm_t.CRC32) hash_cur;
    Hash<bit<16>>(HashAlgorithm_t.CRC32) hash_prv;
#endif

    action drop() {
        //drop_ctl = 0x1; // Drop Packet. Set to 0x0 to clear drop packet. 
        ig_md.flags.drop = true;
    }


    /* ---------- IPv4 LPM Table ---------- */
    action set_nh_index(bit<16> cur_nh_offset, bit<16> cur_nh_count,
                 bit<16> prv_nh_offset, bit<16> prv_nh_count) {

        ig_md.cur_nh_offset = cur_nh_offset;
        ig_md.cur_nh_count = cur_nh_count;
        ig_md.prv_nh_offset = prv_nh_offset;
        ig_md.prv_nh_count = prv_nh_count;
    }

    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm @name("dstAddr");
        }
        actions = { set_nh_index; drop; NoAction; }
        size = 1024;
        default_action = NoAction();
    }


    /* ---------- Current and Previous Nexthop Tables ---------- */
    action set_nexthop(ip4Addr_t nexthop) {
        ig_md.nh_addr = nexthop;
    }

    table cur_nh {
        key = { ig_md.nh_index: exact @name("nh_index"); }
        actions = { set_nexthop; drop; NoAction; }
        size = 8192;
        default_action = NoAction();
    }

    table prv_nh {
        key = { ig_md.nh_index: exact @name("nh_index"); }
        actions = { set_nexthop; drop; NoAction; }
        size = 8192;
        default_action = NoAction();
    }


    /* ---------- Neighbor Table ---------- */
    action set_output(macAddr_t dstMac, PortId_t port) {
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        hdr.ethernet.dstAddr = dstMac;
        /* XXX no need to swap src mac? */
        hdr.ethernet.srcAddr = 0x0200000000FF;
        egress_port = port;
    }

    table neigh {
        key = { ig_md.nh_addr: exact @name("nh_addr"); }
        actions = { set_output; drop; NoAction; }
        size = 1024;
        default_action = NoAction();
    }



    /* ---------- ECMP-ER Logic ---------- */
    apply {
        if (ig_md.flags.ipv4_checksum_error){
            drop();
        }

        /* extract port numbers */
        if (hdr.tcp.isValid()) {
            ig_md.srcPort = hdr.tcp.srcPort;
            ig_md.dstPort = hdr.tcp.dstPort;
        } else if (hdr.udp.isValid()) {
            ig_md.srcPort = hdr.udp.srcPort;
            ig_md.dstPort = hdr.udp.dstPort;
        } else {
            ig_md.srcPort = 0;
            ig_md.dstPort = 0;
        }
    
        if (hdr.ipv4.isValid() && hdr.ipv4.ttl > 0) {

            bit<16> prv_nh_hash_tmp;    // not used in ECMPER_TNA
            bit<16> cur_nh_hash_tmp;    // not used in ECMPER_TNA
            bit<16> prv_nh_hash_masked;
            bit<16> cur_nh_hash_masked;

            /* get nexthop index */
            ipv4_lpm.apply();

            /* calculate nh index from hash of the packet */
            // nh_count is always power of 2, so that (hash value % nh_count) can be
            // (hash value & (nh_count - 1))
            ig_md.prv_nh_count = ig_md.prv_nh_count - 1;
            ig_md.cur_nh_count = ig_md.cur_nh_count - 1;

#ifdef ECMPER_TNA
            prv_nh_hash_masked = (hash_prv.get(
                {hdr.ipv4.srcAddr, hdr.ipv4.protocol, ig_md.dstPort, ig_md.srcPort}
            ) & ig_md.prv_nh_count);

            cur_nh_hash_masked = (hash_cur.get(
                {hdr.ipv4.srcAddr, hdr.ipv4.protocol, ig_md.dstPort, ig_md.srcPort}
            ) & ig_md.cur_nh_count);
#else
            // range of hash calc result is [base, base+max-1] inclusive
            hash(prv_nh_hash_tmp,
                HashAlgorithm.crc32,
                (bit<16>)0,     // in  base (min value)
                { hdr.ipv4.srcAddr, hdr.ipv4.protocol, ig_md.dstPort, ig_md.srcPort },
                (bit<16>)0xffff // in  max hash value
            );
            prv_nh_hash_masked = (prv_nh_hash_tmp & ig_md.prv_nh_count);

            hash(cur_nh_hash_tmp,
                HashAlgorithm.crc32,
                (bit<16>)0,     // base (min value)
                { hdr.ipv4.srcAddr, hdr.ipv4.protocol, ig_md.dstPort, ig_md.srcPort },
                (bit<16>)0xffff // max hash value
            );
            cur_nh_hash_masked = (cur_nh_hash_tmp & ig_md.cur_nh_count);
#endif

            /* get nexthop address from prevous or current Nexthop Table */
            if (hdr.ipv4.diffserv == TOS_RETRANSMITTED) {
                ig_md.nh_index = prv_nh_hash_masked + ig_md.prv_nh_offset;
                prv_nh.apply();
            } else {
                ig_md.nh_index = cur_nh_hash_masked + ig_md.cur_nh_offset;
                cur_nh.apply();
            }

            /* nh_addr 0.0.0.0 means connected route. use ipv4.dstAddr */
            if (ig_md.nh_addr == 0) {
                ig_md.nh_addr = hdr.ipv4.dstAddr;
            }

            /* set dst mac and output port in accordance with nexthop address */
            neigh.apply();
        }
    }
}
