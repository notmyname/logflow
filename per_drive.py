#!/usr/bin/env python3.7

from collections import defaultdict
import re
import sys

per_drive = defaultdict(list)

storage_log_pattern = r"""
.*?  # remote_addr
\s-\s-\s
\[.*?\]  # datetime
\s
"(.*?)\s(.*?)"  # req method and path
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
                    source,
                    source_pid,
                    trans_time,
                    server_pid,
                    policy,
                ) = m.groups()
                path_parts = path.split("/")
                drive = path_parts[1]
                time_bucket = int(float(trans_time) * 100)
                # print(time_bucket, trans_time)
                time_bucket_str = "%05dms" % ((1 + time_bucket) * 100)
                per_drive[(drive,)].append(line)

for key in sorted(per_drive):
    print(" ".join(key), len(per_drive[key]))
