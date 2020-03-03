#!/usr/bin/env python3.7

import datetime
import sys
import pprint
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.patches as mpatches
from collections import defaultdict
import math
import table_print


@FuncFormatter
def time_formatter(x, pos):
    dt = datetime.datetime.fromtimestamp(x)
    return dt.strftime("%H:%M:%S")


x, y = [], []
colors = []
with open(sys.argv[1], "r") as fp:
    for i, line in enumerate(fp):
        if not i % 50:
            print("\rLines processed: %d..." % i, end="", file=sys.stderr)
            sys.stderr.flush()
        line = line.split()
        if len(line) < 26:
            continue
        if line[4] not in ("proxy-server:", "swift:"):
            continue
        if line[21] != "-":
            continue

        rsyslog_host = line[3]
        method = line[8]
        if method != "GET":
            # only process GET requests
            continue
        # bytes_sent = 0 if line[16] == "-" else int(line[16])
        request_time = float(line[20])
        request_start = float(line[23])

        request_path = line[9]
        if request_path in ("/auth/v1.0", "/info"):
            continue
        if not request_path.startswith("/v1/"):
            request_path = "/v1/FAKE_s3" + request_path
        if request_path.count("/") <= 3:
            # only process objects
            continue
        colors.append(
            {
                1: "#99C94548",  # ???
                2: "#52BCA348",  # account
                3: "#5D69B148",  # container
            }.get(request_path.count("/"), "#E5860648")
        )  # object
        x.append(request_start)
        y.append(request_time)

print("\nDone", file=sys.stderr)


p_measures = [
    (0.5, "P50"),
    (0.9, "P90"),
    (0.95, "P95"),
    (0.99, "P99"),
    (0.999, "P999"),
    # (0.9999, "P9999",),
]


# table for the total span of data
percentile_data = y[:]
percentile_data.sort()
len_data = len(percentile_data)
t = [(None, "%d samples" % len_data)]
for p, name in p_measures:
    i = int(len_data * p)
    val_str = "%.4f" % percentile_data[i]
    t.append((name, val_str))
t.append(("Max", "%.4f" % percentile_data[-1]))
print(table_print.table_print(t))


# latency scatter plot

mpl.rcParams.update(mpl.rcParamsDefault)
fig, ax = plt.subplots(1, 1, figsize=(12, 4))

ax.scatter(x, y, s=1, c=colors)

ax.xaxis.set_major_formatter(time_formatter)

labels = ax.get_xticklabels()
plt.setp(labels, rotation=45, horizontalalignment="right")

unkown_patch = mpatches.Patch(color="#99C94548", label="??")
acct_patch = mpatches.Patch(color="#52BCA348", label="Account")
cont_patch = mpatches.Patch(color="#5D69B148", label="Container")
obj_patch = mpatches.Patch(color="#E5860648", label="Object")

plt.legend(handles=[acct_patch, cont_patch, obj_patch])

plt.title("Request Latencies")

plt.tight_layout()

plt.style.use("fivethirtyeight")
mpl.rcParams["font.sans-serif"] = "B612"
mpl.rcParams["font.family"] = "B612"
mpl.rcParams["axes.labelsize"] = 10
mpl.rcParams["xtick.labelsize"] = 8
mpl.rcParams["ytick.labelsize"] = 8
mpl.rcParams["text.color"] = "k"

fig.savefig("request_latencies.png")

print("Done with request_latencies.png")


# rolling latencies chart

sorted_value_pairs = [(x[i], y[i]) for i in range(len(x))]
sorted_value_pairs.sort()
latency_rolling_data = defaultdict(list)


class LatencyCounter(object):
    def __init__(self):
        self.buckets = defaultdict(list)

    def add(self, start, end, val):
        start = int(start)
        end = int(math.ceil(end))
        if end == start:
            end += 1
        for i in range(start, end, 1):
            self.buckets[i].append(val)


latency_over_time = LatencyCounter()
for t, val in sorted_value_pairs:
    latency_over_time.add(t, t + val, val)

time_buckets = list(latency_over_time.buckets.keys())
time_buckets.sort()


for lookback_seconds in (5, 10, 30, 60, 900):
    mpl.rcParams.update(mpl.rcParamsDefault)
    fig, ax = plt.subplots(1, 1, figsize=(12, 4))

    for p, name in p_measures:
        plotable_x = []
        plotable_y = []
        for t in time_buckets[lookback_seconds:]:
            t_start = t - lookback_seconds
            all_timings = []
            for t2 in range(t_start, t):
                all_timings.extend(latency_over_time.buckets[t2])
            all_timings.sort()
            p_index = int(len(all_timings) * p)

            plotable_x.append(t)
            plotable_y.append(all_timings[p_index])

        ax.plot(
            plotable_x,
            plotable_y,
            label=name,
            linestyle="-",
            marker="None",
            alpha=0.4,
        )

    plt.title("Rolling Request Latencies, Every %d Seconds" % lookback_seconds)

    ax.legend(loc="best", fancybox=True)
    ax.xaxis.set_major_formatter(time_formatter)

    plt.tight_layout()

    plt.style.use("fivethirtyeight")
    mpl.rcParams["font.sans-serif"] = "B612"
    mpl.rcParams["font.family"] = "B612"
    mpl.rcParams["axes.labelsize"] = 10
    mpl.rcParams["xtick.labelsize"] = 8
    mpl.rcParams["ytick.labelsize"] = 8
    mpl.rcParams["text.color"] = "k"

    outname = "rolling_request_latencies_%dsec.png" % lookback_seconds

    fig.savefig(outname)

    print(f"Done with {outname}")
