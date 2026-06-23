#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

NORMAL = RESULTS / "v25a_mlkem_only_mlkem_stack_usage.csv"
NOINLINE = RESULTS / "v25a_noinline_mlkem_stack_usage.csv"
OUT = RESULTS / "v25a_mlkem_normal_vs_noinline.md"

TARGETS = [
    "indcpa_keypair_derand",
    "indcpa_enc",
    "indcpa_dec",
]


def load(path):
    rows = []

    with path.open() as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["bytes"] = int(row["bytes"])
            rows.append(row)

    return rows


def best_match(rows, variant, target):
    matches = [
        r for r in rows
        if r["variant"] == variant and target in r["function"]
    ]

    if not matches:
        return None

    matches.sort(key=lambda r: r["bytes"], reverse=True)
    return matches[0]


normal_rows = load(NORMAL)
noinline_rows = load(NOINLINE)

md = "# v25a ML-KEM normal vs no-inline stack comparison\n\n"
md += "| Variant | Target | Normal bytes | Normal kind | No-inline bytes | No-inline kind | Difference | Interpretation |\n"
md += "|---|---|---:|---|---:|---|---:|---|\n"

for variant in ["x86_64", "ref"]:
    for target in TARGETS:
        n = best_match(normal_rows, variant, target)
        ni = best_match(noinline_rows, variant, target)

        n_bytes = n["bytes"] if n else 0
        ni_bytes = ni["bytes"] if ni else 0
        n_kind = n["kind"] if n else "missing"
        ni_kind = ni["kind"] if ni else "missing"
        diff = n_bytes - ni_bytes

        if n_bytes == 0 or ni_bytes == 0:
            interp = "missing data"
        elif abs(diff) <= 256:
            interp = "local-buffer dominated"
        elif n_bytes > ni_bytes:
            interp = "partly inlining-related"
        else:
            interp = "no-inline not smaller"

        md += (
            f"| {variant} | {target} | {n_bytes} | {n_kind} | "
            f"{ni_bytes} | {ni_kind} | {diff} | {interp} |\n"
        )

OUT.write_text(md)

print(f"wrote {OUT}")
