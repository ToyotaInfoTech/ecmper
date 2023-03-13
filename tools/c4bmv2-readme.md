# c4bmv2: controller 4 bmv2

A Python program which provides REST API and control ECMP-ER Router (bmv2)

## c4bmv2 usage

```
@app.route("/add/<prefix>/<int:preflen>/<nexthop>", methods = ["PUT"])
@app.route("/del/<prefix>/<int:preflen>/<nexthop>",  methods = ["PUT"])
@app.route("/install", methods = ["PUT"])
@app.route("/neigh/add/<nh_addr>/<int:port>/<dstmac>", methods = ["PUT"])
@app.route("/neigh/del/<nh_addr>", methods = ["PUT"])
@app.route("/clear", methods = ["PUT"])
@app.route("/tables", methods = ["GET"])
```

## Examples using [httpie cli](https://httpie.io/cli)

- add neighbor: `http PUT localhost:5000/neigh/add/10.1.0.1/132/24:8a:07:b3:0c:6a`
- add route: `http PUT localhost:5000/neigh/add/10.1.0.0/24/connected`
- add route: `http PUT localhost:5000/neigh/add/10.0.10.0/32/10.0.1.1`
- `/install` deploy queued routes to be appended or deleted into ASIC.
- `/clear` clears all states on both ASIC and Controller.
- show all tables: `http http://localhost:5000/tables`

Adding and Removing 10.0.10.0/32 routes causes ECMP-ER.

