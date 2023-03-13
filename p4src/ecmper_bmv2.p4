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

#define V1MODEL_VERSION 20220415

#include <core.p4>
#include <v1model.p4>

#include "headers.p4"
#include "parser_bmv2.p4"
#include "ecmper.p4"

// ---------------------------------------------------------------------------
// Ingress Control
// ---------------------------------------------------------------------------
control SwitchIngress(
            inout headers_t hdr,
            inout ingress_metadata_t ig_md,
            inout standard_metadata_t st_md) {

    ECMPER() ecmper;

    apply {
        ecmper.apply(
            hdr,
            ig_md,
            st_md.egress_spec
        );
        if (ig_md.flags.drop){
            mark_to_drop(st_md);
        }
    }
}

// ---------------------------------------------------------------------------
// Egress Control
// ---------------------------------------------------------------------------
control SwitchEgress(
            inout headers_t hdr,
            inout ingress_metadata_t ig_md,
            inout standard_metadata_t st_md) {
    apply {

    }
}


// ---------------------------------------------------------------------------
// BMv2 v1model pipeline
// ---------------------------------------------------------------------------
V1Switch(
    SwitchParser(),
    //SwitchVerifyChecksum(),
    NoSwitchVerifyChecksum(),
    SwitchIngress(),
    SwitchEgress(),
    SwitchComputeChecksum(),
    //NoSwitchComputeChecksum(),
    SwitchDeparser()
) main;