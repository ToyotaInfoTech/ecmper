# ECMP-ER ... Extending ECMP toward A Practical Hardware Load Balancer

This repository provides English description and code/script to DEMO ECMP-ER.

- [LICENSES](#licenses)
- [What is ECMP-ER ?](#what-is-ecmp-er-)
- [DEMO code and script](#demo-code-and-script)
- [Authors](#authors)


## LICENSES

- P4 Source Code under [p4src/](p4src/) are licensed under Apache License, Version 2.0
- XDP source code under [xdp/](xdp/) are indicated by the SPDX license headers in individual source files

## What is ECMP-ER ?

Motivation of this work was from the growth of upstream traffic from connected cars and lack of simple and scalable way to balance such upstream traffic, which lead to scalable direction agnostic loadbalancing mechanism which could run on commodity switch/router hardware.

More details about the motivation and how ECMP-ER works are described in below slides.

- Slides: [ecmper-english-IOTS2022.pdf](ecmper-english-IOTS2022.pdf)

ECMP-ER was accepted at IOTS2022 and a paper in **Japanese** is available to conference attendees and paid download.

- [IOTS2022 Program page (Japanese) ](https://www.iot.ipsj.or.jp/symposium/iots2022-program/)
- [Abstract (English) and download page of the IOTS2022 paper (Japanese)](https://ipsj.ixsq.nii.ac.jp/ej/?action=pages_view_main&active_action=repository_view_main_item_detail&item_id=222743&item_no=1&page_id=13&block_id=8)

## DEMO code and script

> Note: DEMO P4/XDP code and scripts are NOT identical to the ones used in the IOTS2022 paper which Tofino was used.

You can run ECMP-ER using BMv2 on Ubuntu (without Tofino Box) following below instructions.

- [How to run demo (markdown)](./HOWTO-ECMPER-DEMO.md)
  - Setup BMv2 environment and Build P4/XDP
  - Demo Topology and common setup
  - Demo 1: Manually confirm ECMP-ER operation
  - Demo 2: Apache Bench
- [How to run demo slides (pdf)](./HOWTO-ECMPER-DEMO-slides.pdf)
  - Demo Topology
  - P4 Tables and Pipeline
  - "controller 4 bmv2" a.k.a c4bmv2 design
  - Server side XDP client logic
  - Packet flow when ECMP ER is enabled / disabled (Demo 1)
- Source code and scripts
  - [P4 Source Code](./p4src/)
  - [XDP code and scripts](./xdp/)
  - [misc scripts](./tools/)

## Authors

Authors of the ECMP-ER Paper (IOTS2022)

- Ryo Nakamura [1]
- Kentaro Ebisawa [2]
- Tomoko Okuzawa [2]
- Chunghan Lee [2]
- Yuji Sekiya [1]

P4 Source Code and documents *on this site* is created by below member with support from Authors of ECMP-ER paper.

- Kentaro Ebisawa [2]

[1] Information Technology Center, The University of Tokyo
[2] Toyota Motor Corporation
