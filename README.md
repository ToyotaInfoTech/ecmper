# ECMP-ER ... Extending ECMP toward A Practical Hardware Load Balancer

This repository provides English description and code/script to DEMO ECMP-ER.

- [What is ECMP-ER ?](#what-is-ecmp-er-)
- [DEMO code and script (WIP: 2023 Q1)](#demo-code-and-script-wip-2023-q1)
- [Authors](#authors)

## What is ECMP-ER ?

Motivation of this work was from the growth of upstream traffic from connected cars and lack of simple and scalable way to balance such upstream traffic, which lead to scalable direction agnostic loadbalancing mechanism which could run on commodity switch/router hardware.

More details about the motivation and how ECMP-ER works are described in below slides.

- Slides: [ecmper-english-IOTS2022.pdf](ecmper-english-IOTS2022.pdf)

ECMP-ER was accepted at IOTS2022 and a paper in **Japanese** is available to conference attendees and paid download.

- [IOTS2022 Program page (Japanese) ](https://www.iot.ipsj.or.jp/symposium/iots2022-program/)
- [Abstract (English) and download page of the IOTS2022 paper (Japanese)](https://ipsj.ixsq.nii.ac.jp/ej/?action=pages_view_main&active_action=repository_view_main_item_detail&item_id=222743&item_no=1&page_id=13&block_id=8)

## DEMO code and script (WIP: 2023 Q1)

> DEMO is still WIP and planned to be published around 2023 Q1.

> Note that the DEMO P4/XDP code and scripts are NOT identical to the ones used in the IOTS2022 paper.

- How to run demo
  - [TBD: slides]()
- Demo P4 Source Code (BMv2), XDP source code and scripts to test ECMP-ER on Linux Server (without Tofino Box)
  - [TBD: P4 Source Code]()
  - [TBD: XDP code and scripts]()

## Authors

Authors of the ECMP-ER Paper (IOTS2022)

- Ryo Nakamura [1]
- Kentaro Ebisawa [2]
- Tomoko Okuzawa [2]
- Chunghan Lee [2]
- Yuji Sekiya [1]

P4 Source Code and documents on this site is created by below member with support from Authors of ECMP-ER paper.

- Kentaro Ebisawa [2]

[1] Information Technology Center, The University of Tokyo
[2] Toyota Motor Corporation
