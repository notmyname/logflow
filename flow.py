#!/usr/bin/env python

import re
import sys
import argparse
import pygraphviz as pgv


parser = argparse.ArgumentParser()
parser.add_argument("--use-server-type", default=False, action="store_true")
parser.add_argument(
    "--show-response-codes", default=False, action="store_true"
)
parser.add_argument("filename")
args = parser.parse_args()

storage_log_pattern = r"""
.*?  # remote_addr
\s-\s-\s
\[.*?\]  # datetime
\s
"(.*?)\s.*?"  # req method and path
\s
(\d\d\d)  # status int
\s
.*?  # content length
\s
".*?"  # referrer
\s
".*?"  # txn id
\s
"(.*?)\s(\d*?)"  # user agent
\s
.*?  # transaction time
\s
(\d{1,6})  # server pid
"""

auth_pattern = r"""
User:\s
.*?  # user id
uses\stoken\s
.*?\s
\(trans_id .*?\)
"""

storage_log_regex = re.compile(storage_log_pattern, re.VERBOSE | re.MULTILINE)
auth_pattern_regex = re.compile(auth_pattern, re.VERBOSE | re.MULTILINE)

st_map = {"obj-server": "object-server", "swift": "container-reconciler"}

g = pgv.AGraph(
    strict=False,
    directed=True,
    overlap="prism",
    overlap_shrink="true",
    sep=".25",
    splines="spline",
    fontname="B612",
    fontsize=12,
    pack="true",
)
servers_found = set()

edge_tracker = dict()

max_found_edge_weight = 0
max_edge_weight = 5


def _add_edge(s1, s2, method, status):
    global max_found_edge_weight
    if not args.show_response_codes:
        status = ""
    key = s1 + s2 + method + status
    if method or status:
        if status:
            label = "%s (%s)" % (method, status)
        else:
            label = method
    else:
        label = ""

    if key in edge_tracker:
        edge_tracker[key][2] += 1
    else:
        edge_tracker[key] = [(s1, s2, method), label, 1]
    max_found_edge_weight = max(edge_tracker[key][2], max_found_edge_weight)


def _write_edges():
    for edge in edge_tracker.values():
        (src, target, method), label, count = edge
        label = "%dx %s" % (count, label) if label else "%dx" % (count)
        edge_thickness = max(
            float(count) / max_found_edge_weight * max_edge_weight, 1.0
        )
        g.add_edge(
            src, target, label=label, weight=count, penwidth=edge_thickness
        )


with open(args.filename, "rb") as f:
    for rawline in f:
        rawline = rawline.strip()
        if not rawline or rawline.startswith("#"):
            continue
        line = rawline[16:]  # pull off syslog timestamp
        if not line:
            continue
        server_name, line = line.split(" ", 1)
        server_type, line = line.split(": ", 1)
        server_type = st_map.get(server_type.strip(), server_type.strip())
        m = storage_log_regex.match(line)
        if m:
            (method, status, source, source_pid, server_pid) = m.groups()
            if args.use_server_type:
                source_pid = ""
                server_pid = ""
            source = st_map.get(source, source)
            source = "%s %s" % (source, source_pid)
            dest = "%s %s" % (server_type, server_pid)
            _add_edge(source, dest, method, status)
        else:
            m = auth_pattern_regex.match(line)
            if m:
                _add_edge("proxy-server", "auth", "", "")

_write_edges()
g.graph_attr["ratio"] = "0.618"
if args.use_server_type:
    prog = "fdp"
else:
    prog = "twopi"
g.layout(prog=prog)
g.draw("out.png", prog=prog)
