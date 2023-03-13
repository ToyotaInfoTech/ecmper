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

parser SwitchParser(
        packet_in pkt,
        out headers_t hdr,
        inout ingress_metadata_t ig_md,
        inout standard_metadata_t ig_intr_md) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            IPPROTO_TCP: parse_tcp;
            IPPROTO_UDP: parse_udp;
            default: accept;
        }
    }

    state parse_tcp {
        pkt.extract(hdr.tcp);
        transition accept;
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        transition accept;
    }
}

// -----------------------------------------------------------------------------
// Egress Parser
// -----------------------------------------------------------------------------

// Egress Parser - No Egress Parser for v1model

// -----------------------------------------------------------------------------
// Deparser
// -----------------------------------------------------------------------------
control SwitchDeparser(
        packet_out pkt,
        in headers_t hdr) {

    apply {
        pkt.emit(hdr.ethernet);
        pkt.emit(hdr.ipv4);
        pkt.emit(hdr.tcp);
        pkt.emit(hdr.udp);
    }
}

// No EgressDeparser for v1model


// -----------------------------------------------------------------------------
// BMv2 v1model Checksum
// -----------------------------------------------------------------------------
control NoSwitchVerifyChecksum(
            inout headers_t hdr,
            inout ingress_metadata_t ig_md) {
    // dummy control to skip checkum
    apply { }
}
control SwitchVerifyChecksum(
            inout headers_t hdr,
            inout ingress_metadata_t ig_md) {
    // if checksum error was detected,
    // the value of the standard_metadata checksum_error field
    // will be equal to 1 when the packet begins ingress processing.
    apply {
        verify_checksum(true, {
                hdr.ipv4.version,
                hdr.ipv4.ihl,
                hdr.ipv4.diffserv,
                hdr.ipv4.totalLen,
                hdr.ipv4.identification,
                hdr.ipv4.flags,
                hdr.ipv4.fragOffset,
                hdr.ipv4.ttl,
                hdr.ipv4.protocol,
                hdr.ipv4.srcAddr,
                hdr.ipv4.dstAddr
            },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16
        );
    }
}
control NoSwitchComputeChecksum(
            inout headers_t hdr,
            inout ingress_metadata_t ig_md) {
    // dummy control to skip checkum
    apply { }
}
control SwitchComputeChecksum(
            inout headers_t hdr,
            inout ingress_metadata_t ig_md) {
    apply {
        update_checksum(true, {
                hdr.ipv4.version,
                hdr.ipv4.ihl,
                hdr.ipv4.diffserv,
                hdr.ipv4.totalLen,
                hdr.ipv4.identification,
                hdr.ipv4.flags,
                hdr.ipv4.fragOffset,
                hdr.ipv4.ttl,
                hdr.ipv4.protocol,
                hdr.ipv4.srcAddr,
                hdr.ipv4.dstAddr
            },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16
        );
    }
}