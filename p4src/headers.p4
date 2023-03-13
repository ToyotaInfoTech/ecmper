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

const bit<16>   TYPE_IPV4 = 0x800;
const bit<8>    IPPROTO_TCP = 6;
const bit<8>    IPPROTO_UDP = 17;

const bit<8>    TOS_RETRANSMITTED = 0x01;

/* headers */

typedef bit<9> egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
    macAddr_t   dstAddr;
    macAddr_t   srcAddr;
    bit<16>     etherType;
}

header ipv4_t {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    ip4Addr_t   srcAddr;
    ip4Addr_t   dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<3>  res;
    bit<3>  ecn;
    bit<6>  ctrl;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> len;
    bit<16> hdrChecksum;
}

struct ingress_flags_t {
    bool ipv4_checksum_error;
    bool drop;
}
struct ingress_metadata_t { //ig_md (same as eg_md for v1model)
//    bit<1>  retransmitted;  /* flag to use prv_nh for retransmission */
    bit<16> srcPort;
    bit<16> dstPort;

    /* filled by ipv4 LPM table */
    bit<16> cur_nh_offset;
    bit<16> cur_nh_count;
    bit<16> prv_nh_offset;
    bit<16> prv_nh_count;

    /* filled by ECMPER */
    bit<16> nh_index;

    /* filled by Nexthop table pointed by index */
    bit<32> nh_addr;

    ingress_flags_t flags;
}
struct egress_metadata_t { // eg_md
}

struct headers_t {
    ethernet_t  ethernet;
    ipv4_t      ipv4;
    tcp_t       tcp;
    udp_t       udp;
}