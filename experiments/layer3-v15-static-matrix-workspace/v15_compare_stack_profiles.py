#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path


def load_csv(path: Path):
    data = {}

    with path.open() as f:
        reader = csv.DictReader(f)

        for row in reader:
            variant = row.get("variant", "unknown")
            function = row["function"]

            # Use variant + function only.
            # Do not include location because v15 inserted lines into sign.c,
            # so line numbers differ from v14 baseline/reduced-RAM.
            key = (variant, function)

            size = int(row["bytes"])

            if key not in data or size > data[key]["bytes"]:
                data[key] = {
                    "variant": variant,
                    "function": function,
                    "bytes": size,
                    "kind": row["kind"],
                    "location": row["location"],
                }

    return data


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: v15_compare_stack_profiles.py <baseline.csv> <reduce.csv> <static_matrix.csv> <out.md>",
            file=sys.stderr,
        )
        return 2

    baseline = load_csv(Path(sys.argv[1]))
    reduce_ram = load_csv(Path(sys.argv[2]))
    static_matrix = load_csv(Path(sys.argv[3]))
    out = Path(sys.argv[4])

    keys = set(baseline) | set(reduce_ram) | set(static_matrix)

    rows = []

    for key in keys:
        b = baseline.get(key, {}).get("bytes", 0)
        r = reduce_ram.get(key, {}).get("bytes", 0)
        s = static_matrix.get(key, {}).get("bytes", 0)

        if max(b, r, s) < 512:
            continue

        base = baseline.get(key) or reduce_ram.get(key) or static_matrix.get(key)

        rows.append({
            "variant": base["variant"],
            "function": base["function"],
            "baseline": b,
            "reduce_ram": r,
            "static_matrix": s,
            "baseline_minus_reduce": b - r,
            "baseline_minus_static": b - s,
            "static_minus_reduce": s - r,
            "location": base["location"],
        })

    rows.sort(key=lambda x: (x["variant"] != "x86_64", -x["baseline"], x["function"]))

    with out.open("w") as f:
        f.write("# v15 stack profile comparison\n\n")
        f.write("| Variant | Function | Baseline B | Reduced-RAM B | Static-matrix B | Baseline - Reduced | Baseline - Static | Static - Reduced |\n")
        f.write("|---|---|---:|---:|---:|---:|---:|---:|\n")

        for row in rows[:100]:
            f.write(
                f"| {row['variant']} | `{row['function']}` | "
                f"{row['baseline']} | {row['reduce_ram']} | {row['static_matrix']} | "
                f"{row['baseline_minus_reduce']} | {row['baseline_minus_static']} | {row['static_minus_reduce']} |\n"
            )

    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
