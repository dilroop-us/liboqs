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
            location = row["location"]
            key = (variant, function, location)

            size = int(row["bytes"])
            if key not in data or size > data[key]["bytes"]:
                data[key] = {
                    "variant": variant,
                    "function": function,
                    "bytes": size,
                    "kind": row["kind"],
                    "location": location,
                }
    return data


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: v14_compare_stack_profiles.py <baseline.csv> <reduce.csv> <lazy.csv> <out.md>",
            file=sys.stderr,
        )
        return 2

    baseline = load_csv(Path(sys.argv[1]))
    reduce_ram = load_csv(Path(sys.argv[2]))
    lazy = load_csv(Path(sys.argv[3]))
    out = Path(sys.argv[4])

    keys = set(baseline) | set(reduce_ram) | set(lazy)

    rows = []
    for key in keys:
        b = baseline.get(key, {}).get("bytes", 0)
        r = reduce_ram.get(key, {}).get("bytes", 0)
        l = lazy.get(key, {}).get("bytes", 0)
        max_size = max(b, r, l)

        if max_size < 512:
            continue

        base = baseline.get(key) or reduce_ram.get(key) or lazy.get(key)
        rows.append({
            "variant": base["variant"],
            "function": base["function"],
            "baseline": b,
            "reduce_ram": r,
            "lazy_polyvec": l,
            "delta_baseline_reduce": b - r,
            "delta_baseline_lazy": b - l,
            "location": base["location"],
        })

    rows.sort(key=lambda x: (x["variant"] != "x86_64", -x["baseline"], x["function"]))

    with out.open("w") as f:
        f.write("# v14 stack profile comparison\n\n")
        f.write("| Variant | Function | Baseline B | Reduced-RAM B | Lazy-polyvec B | Baseline - Reduced | Baseline - Lazy | Location |\n")
        f.write("|---|---|---:|---:|---:|---:|---:|---|\n")
        for row in rows[:100]:
            f.write(
                f"| {row['variant']} | `{row['function']}` | {row['baseline']} | {row['reduce_ram']} | "
                f"{row['lazy_polyvec']} | {row['delta_baseline_reduce']} | {row['delta_baseline_lazy']} | "
                f"`{row['location']}` |\n"
            )

    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
