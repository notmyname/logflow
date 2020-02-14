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

with open(sys.argv[1], "r") as fp:
    for i, raw_line in enumerate(fp):
        if not i % 50:
            print("\rLines processed: %d..." % i, end="", file=sys.stderr)
            sys.stderr.flush()
        raw_line = raw_line.strip()
        if not raw_line or raw_line[0] == "#":
            continue

        line = raw_line[16:]  # filter off syslog timestamp

        try:
            server_type, parts = line.split(":", 1)
        except ValueError:
            continue

        server_type = server_type.strip()
        try:
            server_name, server_type = server_type.split()
        except ValueError:
            continue
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

print("\nDone", file=sys.stderr)

table = []
table.append(("Disk", "Ops Count"))
for key in sorted(per_drive):
    table.append((" ".join(key), len(per_drive[key])))
print(table_print(table))
