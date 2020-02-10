#!/usr/bin/env python3.7

import datetime
import sys
import pprint
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


@FuncFormatter
def time_formatter(x, pos):
    dt = datetime.datetime.fromtimestamp(x)
    return dt.strftime("%H:%M:%S")


x, y = [], []
colors = []
with open(sys.argv[1], "r") as fp:
    for i, line in enumerate(fp):
        line = line.split()
        if len(line) < 26:
            continue
        if line[4] != "proxy-server:":
            continue
        if line[21] != "-":
            continue

        rsyslog_host = line[3]
        method = line[8]
        bytes_sent = 0 if line[16] == "-" else int(line[16])
        request_time = float(line[20])
        request_start = float(line[23])

        request_path = line[9]
        if request_path in ("/auth/v1.0", "/info"):
            continue
        if not request_path.startswith("/v1/"):
            request_path = "/v1/FAKE_s3" + request_path
        colors.append(
            {
                1: "#99C94548",  # ???
                2: "#52BCA348",  # account
                3: "#5D69B148",  # container
            }.get(request_path.count("/"), "#E5860648")
        )  # object
        x.append(request_start)
        y.append(request_time)


mpl.rcParams.update(mpl.rcParamsDefault)
fig, ax = plt.subplots(1, 1, figsize=(12, 4))

ax.scatter(x, y, s=1, c=colors)

ax.xaxis.set_major_formatter(time_formatter)

labels = ax.get_xticklabels()
plt.setp(labels, rotation=45, horizontalalignment="right")

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
