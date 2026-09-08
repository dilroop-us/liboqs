#!/usr/bin/env python3

import csv
import math
import statistics
import sys
from pathlib import Path


def percentile(values, p):
    values = sorted(values)

    if not values:
        return 0.0

    if len(values) == 1:
        return float(values[0])

    k = (len(values) - 1) * (p / 100.0)

    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return float(values[int(k)])

    return (
        values[f] * (c - k)
        + values[c] * (k - f)
    )


def load(path):
    rows = []

    with Path(path).open(
        newline="",
        encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            if int(row["status"]) == 0:
                rows.append(int(row["elapsed_ns"]))

    return rows


def report(name, values):
    if not values:
        print(f"{name},ERROR,no successful samples")
        return

    mean = statistics.mean(values)
    median = statistics.median(values)
    stdev = (
        statistics.pstdev(values)
        if len(values) > 1
        else 0.0
    )

    p95 = percentile(values, 95)
    p99 = percentile(values, 99)

    ops_per_second = (
        1_000_000_000.0 / mean
        if mean > 0
        else 0.0
    )

    print(f"TIMING_SUMMARY,{name},samples,{len(values)}")
    print(f"TIMING_SUMMARY,{name},mean_ns,{mean:.3f}")
    print(f"TIMING_SUMMARY,{name},median_ns,{median:.3f}")
    print(f"TIMING_SUMMARY,{name},min_ns,{min(values)}")
    print(f"TIMING_SUMMARY,{name},max_ns,{max(values)}")
    print(f"TIMING_SUMMARY,{name},p95_ns,{p95:.3f}")
    print(f"TIMING_SUMMARY,{name},p99_ns,{p99:.3f}")
    print(f"TIMING_SUMMARY,{name},stdev_ns,{stdev:.3f}")
    print(
        f"TIMING_SUMMARY,{name},"
        f"operations_per_second,{ops_per_second:.3f}"
    )


if len(sys.argv) != 3:
    raise SystemExit(
        "usage: summarize_timing.py "
        "sign.csv verify.csv"
    )

report("sign", load(sys.argv[1]))
report("verify", load(sys.argv[2]))
