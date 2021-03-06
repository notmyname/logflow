#!/usr/bin/env python3.7

import sys
from collections import defaultdict
import datetime
import re
import math
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import ciso8601


TIME_BUCKET_SIZE = 1.0


class ConcurrencyCounter(object):
    def __init__(self, resolution=1):
        self._mult = 1 / resolution
        self.buckets = defaultdict(int)

    def add(self, start, end):
        start = int(start * self._mult)
        end = int(math.ceil(end * self._mult))
        if end == start:
            end += 1
        for i in range(start, end, 1):
            self.buckets[i] += 1


@FuncFormatter
def time_formatter(x, pos):
    x *= TIME_BUCKET_SIZE
    dt = datetime.datetime.fromtimestamp(x)
    return dt.strftime("%H:%M:%S")


month_name_to_number = [
    None,
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


storage_log_pattern = r"""
.*?  # remote_addr
\s-\s-\s
\[(.*?)\]  # datetime
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
(.*?)  # transaction time
\s
"-"  # additional info
\s
(\d{1,6})  # server pid
"""
storage_log_regex = re.compile(storage_log_pattern, re.VERBOSE | re.MULTILINE)


error_line_pattern = r".*? proxy-server: ERROR with .*? server .*? re: Trying to GET .*?: (.*?)Timeout \((.*?)s\)"
error_line_regex = re.compile(error_line_pattern, re.MULTILINE)

internal_counter = ConcurrencyCounter(TIME_BUCKET_SIZE)
external_counter = ConcurrencyCounter(TIME_BUCKET_SIZE)
container_counter = ConcurrencyCounter(TIME_BUCKET_SIZE)
obj_counter = ConcurrencyCounter(TIME_BUCKET_SIZE)

twenty_seconds = datetime.timedelta(seconds=20)

error_timestamps = set()

filename = sys.argv[1]

with open(filename, "r", buffering=65536) as f:
    for i, raw_line in enumerate(f):
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
        parts = parts.strip()
        splitted = parts.split()
        if server_type in ("proxy-server", "swift"):
            try:
                (
                    client_ip,
                    remote_addr,
                    timestamp,
                    method,
                    path,
                    protocol,
                    status_int,
                    referer,
                    user_agent,
                    auth_token,
                    bytes_recvd,
                    bytes_sent,
                    client_etag,
                    transaction_id,
                    headers,
                    request_time,
                    source,
                    log_info,
                    start_time,
                    end_time,
                    policy_index,
                ) = splitted
            except ValueError:
                # not a proxy access log line
                m = error_line_regex.match(line)
                if m:
                    timeout_type, timeout_amt = m.groups()
                    if timeout_type == "Connection":
                        continue
                    ts = datetime.datetime.strptime(
                        "2020 " + raw_line[:15], "%Y %b %d %H:%M:%S"
                    )
                    error_timestamps.add(
                        ts - datetime.timedelta(seconds=float(timeout_amt))
                    )
                continue

            try:
                start_time = float(start_time)
                end_time = float(end_time)
            except ValueError:
                continue
            if source == "-":
                # client request
                external_counter.add(start_time, end_time)
            else:
                # internal request
                internal_counter.add(start_time, end_time)
        elif server_type in ("container-server", "object-server"):
            if "- -" not in line:
                continue
            (datetime_first, datetime_end) = splitted[3:5]
            req_duration = float(splitted[-4])
            logged_time = datetime_first + " " + datetime_end
            logged_time = logged_time[1:-1]  # strip the []
            iso_date = [logged_time[7:11]]
            month_num = "%02d" % month_name_to_number.index(logged_time[3:6])
            iso_date.append(month_num)
            iso_date.append(logged_time[0:2])
            iso_date = "-".join(iso_date)
            iso_date += " " + logged_time[12:20] + logged_time[21:]

            end_timestamp = ciso8601.parse_datetime(iso_date).timestamp()
            start_time = end_timestamp - req_duration
            if server_type == "container-server":
                container_counter.add(start_time, end_timestamp)
            elif server_type == "object-server":
                obj_counter.add(start_time, end_timestamp)
            # m = storage_log_regex.match(parts)
            # if m:
            #     (
            #         logged_time,
            #         method,
            #         status,
            #         source,
            #         source_pid,
            #         req_duration,
            #         server_pid,
            #     ) = m.groups()
            #     end_timestamp = dateutil.parser.parse(
            #         logged_time[:11] + " " + logged_time[12:]
            #     )
            #     req_duration = datetime.timedelta(seconds=float(req_duration))
            #     start_time = end_timestamp - req_duration
            #     if server_type == "container-server":
            #         container_counter.add(
            #             start_time.timestamp(), end_timestamp.timestamp()
            #         )
            #     elif server_type == "object-server":
            #         obj_counter.add(
            #             start_time.timestamp(), end_timestamp.timestamp()
            #         )

print("\nDone", file=sys.stderr)


mpl.rcParams.update(mpl.rcParamsDefault)
fig, ax = plt.subplots(1, 1, figsize=(12, 4))

for counter, label in (
    # (internal_counter, "Internal Requests"),
    (external_counter, "Client Requests"),
    (container_counter, "Container Requests"),
    (obj_counter, "Object Requests"),
):
    plotable_x = []
    plotable_y = []
    for k in sorted(counter.buckets):
        plotable_x.append(k)
        plotable_y.append(counter.buckets[k])

    ax.plot(plotable_x, plotable_y, label=label, linestyle="-", marker="None")

# for ts in error_timestamps:
#     plt.axvline(x=ts.timestamp(), color="#469bcf", linewidth=1)

ax.xaxis.set_major_formatter(time_formatter)
ax.legend(loc="best", fancybox=True)

labels = ax.get_xticklabels()
plt.setp(labels, rotation=45, horizontalalignment="right")

plt.title("Concurrent Requests Over Time (%ss resolution)" % TIME_BUCKET_SIZE)

plt.tight_layout()

plt.style.use("fivethirtyeight")
mpl.rcParams["font.sans-serif"] = "B612"
mpl.rcParams["font.family"] = "B612"
mpl.rcParams["axes.labelsize"] = 10
mpl.rcParams["xtick.labelsize"] = 8
mpl.rcParams["ytick.labelsize"] = 8
mpl.rcParams["text.color"] = "k"

fig.savefig("proxy_concurrency.png")
