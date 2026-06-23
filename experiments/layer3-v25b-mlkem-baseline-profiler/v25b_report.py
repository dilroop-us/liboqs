#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v25b_mlkem_baseline_profiler_report.md"

SPEED = RESULTS / "v25b_mlkem_speed.csv"
CORRECTNESS = RESULTS / "v25b_mlkem_correctness.csv"
SIZE = RESULTS / "v25b_mlkem_size.csv"


def load_csv(path):
    if not path.exists():
        return []

    with path.open() as f:
        return list(csv.DictReader(f))


speed_rows = load_csv(SPEED)
correctness_rows = load_csv(CORRECTNESS)
size_rows = load_csv(SIZE)

md = "# Layer 3 v25b: ML-KEM-768 Baseline Operation Profiler\n\n"

md += "## Goal\n\n"
md += (
    "Measure ML-KEM-768 keypair, encapsulation, and decapsulation speed before "
    "making ML-KEM workspace modifications.\n\n"
)

md += "v25b does not patch ML-KEM code. It establishes the speed, size, and correctness baseline for later v26b/v27b/v28b workspace experiments.\n\n"

md += "## Build profiles\n\n"
md += "| Profile | Minimal build | Purpose |\n"
md += "|---|---|---|\n"
md += "| mlkem_only | `KEM_ml_kem_768` | Clean ML-KEM baseline speed |\n"
md += "| combined | `KEM_ml_kem_768;SIG_ml_dsa_44` | Full project context with ML-DSA v24b flags |\n\n"

md += "## Correctness smoke test\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in correctness_rows:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Final speed result\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in speed_rows:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Binary size\n\n"
md += "| Profile | text | data | bss | dec | hex | Binary |\n"
md += "|---|---:|---:|---:|---:|---|---|\n"

for row in size_rows:
    md += (
        f"| {row['profile']} | {row['text']} | {row['data']} | {row['bss']} | "
        f"{row['dec']} | {row['hex']} | `{row['binary']}` |\n"
    )

md += "\n## Interpretation\n\n"
md += (
    "The `mlkem_only` profile is the clean baseline for ML-KEM. "
    "The `combined` profile checks that ML-KEM performance remains comparable in the full project build where ML-DSA v24b is also included.\n\n"
)

md += "These v25b numbers become the reference point for later ML-KEM workspace versions:\n\n"
md += "- v26b: caller workspace for `indcpa_enc`\n"
md += "- v27b: caller workspace for `indcpa_keypair_derand`\n"
md += "- v28b: caller workspace for `indcpa_dec`\n\n"

md += "## Safety rule\n\n"
md += (
    "Later ML-KEM optimization versions should only move local stack buffers into explicit caller-provided workspace. "
    "They should not change ML-KEM arithmetic, randomness, hashing, constant-time comparison, decapsulation failure handling, or ciphertext verification behavior.\n"
)

OUT.write_text(md)

print(f"wrote {OUT}")
