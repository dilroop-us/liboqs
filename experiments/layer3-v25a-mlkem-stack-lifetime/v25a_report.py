#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v25a_mlkem_report.md"

ONLY_CSV = RESULTS / "v25a_mlkem_only_mlkem_stack_usage.csv"
COMBINED_CSV = RESULTS / "v25a_combined_mlkem_stack_usage.csv"
NOINLINE_CSV = RESULTS / "v25a_noinline_mlkem_stack_usage.csv"

ONLY_VS_COMBINED_MD = RESULTS / "v25a_mlkem_only_vs_combined.md"
NORMAL_VS_NOINLINE_MD = RESULTS / "v25a_mlkem_normal_vs_noinline.md"
LIFETIME_MD = RESULTS / "v25a_mlkem_lifetime_map.md"

TARGETS = [
    "indcpa_keypair_derand",
    "indcpa_enc",
    "indcpa_dec",
]


def load_rows(path):
    rows = []

    if not path.exists():
        return rows

    with path.open() as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["bytes"] = int(row["bytes"])
            rows.append(row)

    return rows


def find_target(rows, variant, target):
    matches = [
        r for r in rows
        if r["variant"] == variant and target in r["function"]
    ]

    if not matches:
        return None

    matches.sort(key=lambda r: r["bytes"], reverse=True)
    return matches[0]


only_rows = load_rows(ONLY_CSV)

md = "# Layer 3 v25a: ML-KEM-768 Stack and Lifetime Analysis\n\n"

md += "## Goal\n\n"
md += (
    "Analyze ML-KEM-768 stack usage before making ML-KEM implementation changes. "
    "v25a does not patch ML-KEM code. It identifies stack hotspots and local-buffer candidates for future caller-workspace optimization.\n\n"
)

md += "## Build profiles\n\n"
md += "| Profile | Minimal build | Purpose |\n"
md += "|---|---|---|\n"
md += "| mlkem_only | `KEM_ml_kem_768` | Clean ML-KEM stack analysis |\n"
md += "| combined | `KEM_ml_kem_768;SIG_ml_dsa_44` | Validate ML-KEM results in full project context with ML-DSA v24b flags |\n"
md += "| noinline | `KEM_ml_kem_768` with no-inline flags | Check if ML-KEM stack frames are local-buffer dominated |\n\n"

md += "## Target internal functions\n\n"
md += "- `indcpa_keypair_derand`\n"
md += "- `indcpa_enc`\n"
md += "- `indcpa_dec`\n\n"

md += "## ML-KEM-only target stack frames\n\n"
md += "| Variant | Function | Bytes | Kind | Location |\n"
md += "|---|---|---:|---|---|\n"

for variant in ["x86_64", "ref"]:
    for target in TARGETS:
        row = find_target(only_rows, variant, target)

        if row is None:
            md += f"| {variant} | `{target}` | 0 | missing | missing |\n"
        else:
            md += (
                f"| {variant} | `{row['function']}` | {row['bytes']} | "
                f"{row['kind']} | `{row['location']}` |\n"
            )

md += "\n## ML-KEM-only vs combined-build comparison\n\n"

if ONLY_VS_COMBINED_MD.exists():
    md += ONLY_VS_COMBINED_MD.read_text()
else:
    md += "No ML-KEM-only vs combined comparison found.\n"

md += "\n## Normal vs no-inline comparison\n\n"

if NORMAL_VS_NOINLINE_MD.exists():
    md += NORMAL_VS_NOINLINE_MD.read_text()
else:
    md += "No normal vs no-inline comparison found.\n"

md += "\n## Lifetime map\n\n"

if LIFETIME_MD.exists():
    md += LIFETIME_MD.read_text()
else:
    md += "No lifetime map found.\n"

md += "\n## Interpretation\n\n"
md += (
    "The ML-KEM-only and combined stack sizes match, so the ML-KEM stack hotspots are independent of whether ML-DSA is included in the project build. "
    "The normal and no-inline stack sizes are also very close, so the target functions are local-buffer dominated. "
    "Future versions should move large local buffers from stack to explicit caller-provided workspace.\n\n"
)

md += "## Recommended next versions\n\n"
md += "| Version | Goal |\n"
md += "|---|---|\n"
md += "| v25b | ML-KEM baseline operation profiler for keypair/encaps/decaps |\n"
md += "| v26a | More precise ML-KEM source/lifetime map if needed |\n"
md += "| v26b | Caller workspace for `indcpa_enc` |\n"
md += "| v27b | Caller workspace for `indcpa_keypair_derand` |\n"
md += "| v28b | Caller workspace for `indcpa_dec` |\n"
md += "| v29a | Compact ML-KEM lifecycle workspace layout analysis |\n"
md += "| v29b | Compact ML-KEM lifecycle workspace API |\n\n"

md += "## Safety rule\n\n"
md += (
    "Future ML-KEM patches should only move storage location from stack to caller workspace. "
    "Do not change constant-time comparison, failure handling, decapsulation selection logic, hashing, randomness, compression, or polynomial arithmetic.\n"
)

OUT.write_text(md)

print(f"wrote {OUT}")
