#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

ONLY = RESULTS / "v25a_mlkem_only_mlkem_stack_usage.csv"
COMBINED = RESULTS / "v25a_combined_mlkem_stack_usage.csv"
OUT = RESULTS / "v25a_mlkem_only_vs_combined.md"

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


only_rows = load(ONLY)
combined_rows = load(COMBINED)

md = "# v25a ML-KEM-only vs combined-build stack comparison\n\n"
md += "| Variant | Target | ML-KEM-only bytes | Combined bytes | Difference | Interpretation |\n"
md += "|---|---|---:|---:|---:|---|\n"

for variant in ["x86_64", "ref"]:
    for target in TARGETS:
        o = best_match(only_rows, variant, target)
        c = best_match(combined_rows, variant, target)

        o_bytes = o["bytes"] if o else 0
        c_bytes = c["bytes"] if c else 0
        diff = c_bytes - o_bytes

        if o_bytes == c_bytes and o_bytes != 0:
            interp = "same in clean and combined build"
        elif o_bytes == 0 or c_bytes == 0:
            interp = "missing data"
        else:
            interp = "different; inspect build flags/source selection"

        md += f"| {variant} | {target} | {o_bytes} | {c_bytes} | {diff} | {interp} |\n"

OUT.write_text(md)

print(f"wrote {OUT}")
