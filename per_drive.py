#!/usr/bin/env python3.7

from collections import defaultdict
import re
import sys

from table_print import table_print

per_drive = defaultdict(list)
size_by_drive = defaultdict(int)

storage_log_pattern = r"""
.*?  # remote_addr
\s-\s-\s
\[.*?\]  # datetime
\s
"(.*?)\s(.*?)"  # req method and path
\s
(\d\d\d)  # status int
\s
(.*?)  # content length
\s
".*?"  # referrer
\s
".*?"  # txn id
\s
".*?"  # user agent
\s
(.*?)  # transaction time
\s
"-"
\s
(\d{1,6})  # server pid
\s
(\d)  # policy
"""

storage_log_regex = re.compile(storage_log_pattern, re.VERBOSE | re.MULTILINE)

with open(sys.argv[1], "r") as f:
    for line in f:
        line = line.strip()
        if not line.strip():
            continue
        line = line[23:]
        server_type, line = line.split(": ", 1)
        if server_type == "object-server":
            m = storage_log_regex.match(line)
            if m:
                (
                    method,
                    path,
                    status,
                    size,
                    trans_time,
                    server_pid,
                    policy,
                ) = m.groups()
                path_parts = path.split("/")
                drive = path_parts[1]
                time_bucket = int(float(trans_time) * 100)
                time_bucket_str = "%05dms" % ((1 + time_bucket) * 100)
                try:
                    size = int(size)
                except ValueError:
                    size = 0
                size_bucket = size // 2 ** 20
                size_bucket_str = "%02d MiB" % (1 + size_bucket)
                key = (drive,)
                per_drive[key].append(line)
                size_by_drive[key] += size

table = []
table.append(("Disk", "Ops Count"))
for key in sorted(per_drive):
    table.append((" ".join(key), len(per_drive[key])))
print(table_print(table))
