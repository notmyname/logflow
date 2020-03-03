#!/usr/bin/env python3.7

from collections import defaultdict
import sys
import dateutil
import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


color_palette = [
    "#ffffe5",
    "#fff7bc",
    "#fee391",
    "#fec44f",
    "#fe9929",
    "#ec7014",
    "#cc4c02",
    "#993404",
    "#662506",
]


class ConcurrencyCounter(object):
    def __init__(self, resolution=1):
        self._mult = 1 / resolution
        self.buckets = defaultdict(int)

    def add(self, start, end):
        start = int(start * self._mult)
        end = int(end * self._mult)
        if end == start:
            end += 1
        for i in range(start, end, 1):
            self.buckets[i] += 1


TIME_BUCKET_SIZE = 1.0

drive_counters = defaultdict(lambda: ConcurrencyCounter(TIME_BUCKET_SIZE))


@FuncFormatter
def time_formatter(x, pos):
    x *= TIME_BUCKET_SIZE
    dt = datetime.datetime.fromtimestamp(x)
    return dt.strftime("%H:%M:%S")


with open(sys.argv[1], "rb", buffering=10 * 2 ** 20) as fp:
    for i, raw_line in enumerate(fp):
        if not i % 500:
            print("\rLines processed: %d..." % i, end="", file=sys.stderr)
            # sys.stderr.flush()
        raw_line = raw_line.strip()
        if not raw_line or raw_line[0] == b"#":
            continue

        # if i >= 500000:
        #     break

        # early filtering for faster processing
        if b"object-server" not in raw_line:
            continue
        if b"- -" not in raw_line:
            continue

        line = raw_line[16:]  # filter off syslog timestamp

        try:
            server_type, parts = line.split(b":", 1)
        except ValueError:
            continue

        server_type = server_type.strip()
        try:
            server_name, server_type = server_type.split()
        except ValueError:
            continue
        if server_type == b"object-server":
            parts = parts.strip().decode("ascii")
            splitted = parts.split()

            path = splitted[6][:-1]  # take off the last " character
            drive = path.split("/")[1]

            req_duration = float(splitted[-4])
            (datetime_first, datetime_end) = splitted[3:5]
            logged_time = datetime_first + " " + datetime_end
            logged_time = logged_time[1:-1]  # strip the []

            end_timestamp = dateutil.parser.parse(
                logged_time[:11] + " " + logged_time[12:]
            ).timestamp()
            start_time = end_timestamp - req_duration

            drive_counters[drive].add(start_time, end_timestamp)

print("\nDone", file=sys.stderr)


all_drives = list(drive_counters.keys())
all_drives.sort()  # so subsequent runs have the same order
print(len(all_drives))

mpl.rcParams.update(mpl.rcParamsDefault)
fig_height = max(len(all_drives) * 2 / 96, 4)
fig, ax = plt.subplots(1, 1, figsize=(12, fig_height))


# find global min and max to know how to scale colors
global_min = 9999999999
global_max = -1
for drive in all_drives:
    global_min = min(global_min, min(drive_counters[drive].buckets.values()))
    global_max = max(global_max, max(drive_counters[drive].buckets.values()))

print(global_min, global_max)

len_colors = len(color_palette)
bucket_width = (global_max - global_min) / len_colors

# plot drive counters here
# one line per drive, 1px tall with no gaps, change color based on value
for i, drive in enumerate(all_drives):
    plotable_x = []
    color_vals = []
    for k in sorted(drive_counters[drive].buckets):
        plotable_x.append(k)
        color_index = (
            int(
                (drive_counters[drive].buckets[k] - global_min) // bucket_width
            )
            - 1
        )
        color_vals.append(color_palette[color_index])
    ax.scatter(
        plotable_x, [i] * len(plotable_x), s=1, c=color_vals, marker=","
    )

ax.yaxis.set_visible(False)
ax.xaxis.set_major_formatter(time_formatter)
# ax.legend(loc="best", fancybox=True)

labels = ax.get_xticklabels()
plt.setp(labels, rotation=45, horizontalalignment="right")

plt.title(
    "Concurrent Drive Usage Over Time (%ss resolution)" % TIME_BUCKET_SIZE
)

plt.tight_layout()

plt.style.use("fivethirtyeight")
mpl.rcParams["font.sans-serif"] = "B612"
mpl.rcParams["font.family"] = "B612"
mpl.rcParams["axes.labelsize"] = 10
mpl.rcParams["xtick.labelsize"] = 8
mpl.rcParams["ytick.labelsize"] = 8
mpl.rcParams["text.color"] = "k"

fig.savefig("drive_usage.png")
