#!/usr/bin/env python3.7


import sys
import csv
import datetime

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
import numpy as np


@FuncFormatter
def time_formatter(x, pos):
    dt = datetime.datetime.fromtimestamp(x)
    return dt.strftime("%H:%M:%S")


# read a csv file, key off of (server, drive) and values as list.
# store header lines as list of timestamps to iterate over

drive_data = {}
min_val = 9999999999
max_val = -1
with open(sys.argv[1], "r", newline="") as csvfile:
    reader = csv.reader(csvfile)
    first_line = next(reader)
    timestamps = [float(x) for x in first_line[2:]]
    for i, row in enumerate(reader):
        # if i >= 100:
        #     break
        k = (row[0], row[1])
        data_points = [float(x) for x in row[2:]]
        drive_data[k] = data_points
        min_val = min(min_val, min(data_points))
        max_val = max(max_val, max(data_points))

len_timestamps = len(timestamps)

print(
    f"Loaded data on {len(drive_data)} drives across {len_timestamps} timestamps"
)

print(f"Max value found: {max_val}")
print(f"Min value found: {min_val}")

rect_height = 0.25
fig_width = 12
rect_width = (len_timestamps * (timestamps[1] - timestamps[0])) / fig_width
fig_height = rect_height * len(drive_data)
print(fig_width, fig_height)

rects = []
rect_colors = []
yticks = []
# point is, define a box for each "pixel" for the chart
for i, drive in enumerate(drive_data):
    ypos = i * rect_height
    yticks.append((ypos, "%s %s" % (drive[0].split(".")[0], drive[1])))
    for j, k in enumerate(drive_data[drive]):
        xpos = timestamps[j]
        r = Rectangle((xpos, ypos), rect_width, rect_height)
        rects.append(r)
        color_value = k / max_val
        rect_colors.append(color_value)


mpl.rcParams.update(mpl.rcParamsDefault)
fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))


# Create a collection from the rectangles
col = PatchCollection(rects, cmap="inferno")
col.set_array(np.array(rect_colors))
# No lines
col.set_linewidth(0)
# col.set_edgecolor( 'none' )
# col.set_facecolor(rect_colors)

# Make a figure and add the collection to the axis.
ax.add_collection(col)

ax.set_xlim(timestamps[0], timestamps[-1])
ax.set_ylim(0, len(drive_data) * rect_height)
if rect_height >= 0.125:
    ax.set_yticks([x[0] for x in yticks])
    ax.set_yticklabels([x[1] for x in yticks])
else:
    ax.set_yticks([])
ax.xaxis.set_major_formatter(time_formatter)
labels = ax.get_xticklabels()
plt.setp(labels, rotation=45, horizontalalignment="right")

plt.title("Drive Usage Over Time")

plt.tight_layout()

plt.style.use("fivethirtyeight")
mpl.rcParams["font.sans-serif"] = "B612"
mpl.rcParams["font.family"] = "B612"
mpl.rcParams["axes.labelsize"] = 10
mpl.rcParams["xtick.labelsize"] = 8
mpl.rcParams["ytick.labelsize"] = 8
mpl.rcParams["text.color"] = "k"

fig.savefig("drive_usage.png")
