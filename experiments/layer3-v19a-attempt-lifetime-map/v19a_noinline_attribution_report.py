#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

NORMAL = RESULTS / "v18_workspace_sanitize_stack_usage.csv"
NOINLINE = RESULTS / "v19a_noinline_attribution_stack_usage.csv"
OUT = RESULTS / "v19a_noinline_attribution_report.md"


def normalize(fn: str) -> str:
    if fn.startswith("mld_compute_pack_t0_t1"):
        return "mld_compute_pack_t0_t1"
    return fn


def load(path: Path):
    data = {}

    with path.open() as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row.get("variant") != "x86_64":
                continue

            fn = normalize(row["function"])
            size = int(row["bytes"])

            if fn not in data or size > data[fn]:
                data[fn] = size

    return data


def main() -> int:
    normal = load(NORMAL)
    noinline = load(NOINLINE)

    keys = set(normal) | set(noinline)

    interesting = []
    for fn in keys:
        n = normal.get(fn, 0)
        ni = noinline.get(fn, 0)

        if max(n, ni) < 512:
            continue

        interesting.append((max(n, ni), fn, n, ni, n - ni))

    interesting.sort(reverse=True)

    with OUT.open("w") as f:
        f.write("# v19a no-inline attribution report\n\n")
        f.write("This compares the normal v18 stack profile against a diagnostic no-inline build.\n\n")
        f.write("If a large frame becomes smaller in the no-inline build, the original frame was likely inflated by inlined callees.\n\n")
        f.write("| Function | Normal v18 B | No-inline B | Normal - no-inline |\n")
        f.write("|---|---:|---:|---:|\n")

        for _, fn, n, ni, diff in interesting[:80]:
            f.write(f"| `{fn}` | {n} | {ni} | {diff} |\n")

    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
