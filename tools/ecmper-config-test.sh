#!/usr/bin/env bash

# Neighbor Entries
# @app.route("/neigh/add/<nh_addr>/<int:port>/<dstmac>", methods = ["PUT"])
http PUT localhost:5000/neigh/add/10.0.0.1/1/02:03:04:05:06:01
#http PUT localhost:5000/neigh/add/10.0.0.2/2/02:03:04:05:06:02
#http PUT localhost:5000/neigh/add/10.0.0.3/3/02:03:04:05:06:03
#http PUT localhost:5000/neigh/add/10.0.0.4/4/02:03:04:05:06:04

http PUT localhost:5000/neigh/add/10.0.1.99/0/02:03:04:05:06:99
# http PUT localhost:5000/neigh/del/10.0.1.99

# VIP
# @app.route("/add/<prefix>/<int:preflen>/<nexthop>", methods = ["PUT"])
http PUT localhost:5000/add/10.0.10.0/32/10.0.0.1
#http PUT localhost:5000/add/10.0.10.0/32/10.0.0.2
#http PUT localhost:5000/add/10.0.10.0/32/10.0.0.3
#http PUT localhost:5000/add/10.0.10.0/32/10.0.0.4

# Client
http PUT localhost:5000/add/10.0.1.0/24/connected
#http PUT localhost:5000/del/10.0.1.0/24/connected

# non IPv4 addr (e.g. 0.0.0.1) should be rejected, but not checked
#http PUT localhost:5000/add/10.0.90.0/32/0.0.0.1

# Install Route Entries
http PUT localhost:5000/install

# Show table entries
http localhost:5000/tables
