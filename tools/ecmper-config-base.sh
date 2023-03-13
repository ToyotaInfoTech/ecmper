#!/usr/bin/env bash

# install neighbor and route entries to ECMP-ER Router (bmv2)

# clear all tables (except for drop entry in cur_nh, prv_nh)
http PUT localhost:5000/clear

# Neighbor Entries
# @app.route("/neigh/add/<nh_addr>/<int:port>/<dstmac>", methods = ["PUT"])
http PUT localhost:5000/neigh/add/10.0.0.1/1/02:03:04:05:06:01
http PUT localhost:5000/neigh/add/10.0.0.2/2/02:03:04:05:06:02
http PUT localhost:5000/neigh/add/10.0.0.3/3/02:03:04:05:06:03
http PUT localhost:5000/neigh/add/10.0.0.4/4/02:03:04:05:06:04

http PUT localhost:5000/neigh/add/10.0.1.99/0/02:03:04:05:06:99

# Show table entries
http localhost:5000/tables
