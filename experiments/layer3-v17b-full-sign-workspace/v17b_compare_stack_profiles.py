#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path


def normalize_function(function: str) -> str:
    if function.startswith("mld_compute_pack_t0_t1"):
        return "mld_compute_pack_t0_t1"
    return function


def load_csv(path: Path):
    data = {}
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            function = normalize_function(row["function"])
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
    if len(sys.argv) != 7:
        print("usage: v17b_compare_stack_profiles.py <baseline.csv> <reduce.csv> <v15.csv> <v16.csv> <v17b.csv> <out.md>")
        return 2

    baseline = load_csv(Path(sys.argv[1]))
    reduce_ram = load_csv(Path(sys.argv[2]))
    v15 = load_csv(Path(sys.argv[3]))
    v16 = load_csv(Path(sys.argv[4]))
    v17b = load_csv(Path(sys.argv[5]))
    out = Path(sys.argv[6])

    keys = set(baseline) | set(reduce_ram) | set(v15) | set(v16) | set(v17b)

    rows = []
    for key in keys:
        b = baseline.get(key, {}).get("bytes", 0)
        r = reduce_ram.get(key, {}).get("bytes", 0)
        s15 = v15.get(key, {}).get("bytes", 0)
        s16 = v16.get(key, {}).get("bytes", 0)
        s17 = v17b.get(key, {}).get("bytes", 0)

        if max(b, r, s15, s16, s17) < 512:
            continue

        base = baseline.get(key) or reduce_ram.get(key) or v15.get(key) or v16.get(key) or v17b.get(key)

        rows.append({
            "variant": base["variant"],
            "function": base["function"],
            "baseline": b,
            "reduce_ram": r,
            "v15_static": s15,
            "v16_caller_matrix": s16,
            "v17b_full_sign": s17,
            "baseline_minus_v17b": b - s17,
            "v16_minus_v17b": s16 - s17,
        })

    rows.sort(key=lambda x: (x["variant"] != "x86_64", -max(x["baseline"], x["v16_caller_matrix"], x["v17b_full_sign"]), x["function"]))

    with out.open("w") as f:
        f.write("# v17b stack profile comparison\n\n")
        f.write("| Variant | Function | Baseline B | Reduced-RAM B | v15 static B | v16 matrix B | v17b full sign B | Baseline - v17b | v16 - v17b |\n")
        f.write("|---|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in rows[:120]:
            f.write(
                f"| {row['variant']} | `{row['function']}` | "
                f"{row['baseline']} | {row['reduce_ram']} | {row['v15_static']} | "
                f"{row['v16_caller_matrix']} | {row['v17b_full_sign']} | "
                f"{row['baseline_minus_v17b']} | {row['v16_minus_v17b']} |\n"
            )

    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
