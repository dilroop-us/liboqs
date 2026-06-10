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
            function = row["function"]
            if function.startswith("mld_compute_pack_t0_t1"):
                function = "mld_compute_pack_t0_t1"
            key = (row.get("variant", "unknown"), function)
            size = int(row["bytes"])
            if key not in data or size > data[key]["bytes"]:
                data[key] = {
                    "variant": row.get("variant", "unknown"),
                    "function": function,
                    "bytes": size,
                }
    return data


def main() -> int:
    if len(sys.argv) != 6:
        print("usage: v16_compare_stack_profiles.py <baseline.csv> <reduce.csv> <v15.csv> <v16.csv> <out.md>")
        return 2

    baseline = load_csv(Path(sys.argv[1]))
    reduce_ram = load_csv(Path(sys.argv[2]))
    v15 = load_csv(Path(sys.argv[3]))
    v16 = load_csv(Path(sys.argv[4]))
    out = Path(sys.argv[5])

    keys = set(baseline) | set(reduce_ram) | set(v15) | set(v16)

    rows = []
    for key in keys:
        b = baseline.get(key, {}).get("bytes", 0)
        r = reduce_ram.get(key, {}).get("bytes", 0)
        s15 = v15.get(key, {}).get("bytes", 0)
        s16 = v16.get(key, {}).get("bytes", 0)

        if max(b, r, s15, s16) < 512:
            continue

        base = baseline.get(key) or reduce_ram.get(key) or v15.get(key) or v16.get(key)

        rows.append({
            "variant": base["variant"],
            "function": base["function"],
            "baseline": b,
            "reduce_ram": r,
            "v15_static": s15,
            "v16_caller": s16,
            "baseline_minus_v16": b - s16,
            "v16_minus_v15": s16 - s15,
        })

    rows.sort(key=lambda x: (x["variant"] != "x86_64", -x["baseline"], x["function"]))

    with out.open("w") as f:
        f.write("# v16 stack profile comparison\n\n")
        f.write("| Variant | Function | Baseline B | Reduced-RAM B | v15 static B | v16 caller B | Baseline - v16 | v16 - v15 |\n")
        f.write("|---|---|---:|---:|---:|---:|---:|---:|\n")
        for row in rows[:100]:
            f.write(
                f"| {row['variant']} | `{row['function']}` | "
                f"{row['baseline']} | {row['reduce_ram']} | {row['v15_static']} | {row['v16_caller']} | "
                f"{row['baseline_minus_v16']} | {row['v16_minus_v15']} |\n"
            )

    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
