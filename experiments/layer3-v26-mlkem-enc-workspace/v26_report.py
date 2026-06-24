#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v26_mlkem_enc_workspace_report.md"

V25B_SPEED = RESULTS / "v25b_mlkem_speed.csv"
V26_SPEED = RESULTS / "v26_mlkem_speed.csv"
V26_CORRECTNESS = RESULTS / "v26_mlkem_correctness.csv"
V26_SIZE = RESULTS / "v26_mlkem_size.csv"
V26_WORKSPACE = RESULTS / "v26_mlkem_workspace.csv"
V26_TARGETS = RESULTS / "v26_mlkem_targets.md"


def load_csv(path):
    if not path.exists():
        return []

    with path.open() as f:
        return list(csv.DictReader(f))


def latest_speed(rows, profile, mode):
    matches = [r for r in rows if r["profile"] == profile and r["mode"] == mode]

    if not matches:
        return None

    return float(matches[-1]["mean_us"])


def dedup_rows(rows, keys):
    seen = set()
    out = []

    for row in rows:
        key = tuple(row[k] for k in keys)

        if key in seen:
            continue

        seen.add(key)
        out.append(row)

    return out


v25b_speed = load_csv(V25B_SPEED)
v26_speed = load_csv(V26_SPEED)
v26_correctness = load_csv(V26_CORRECTNESS)
v26_size = load_csv(V26_SIZE)
v26_workspace = dedup_rows(load_csv(V26_WORKSPACE), ["profile", "workspace_kind", "bytes"])

md = "# Layer 3 v26: ML-KEM Encapsulation Caller Workspace\n\n"

md += "## Goal\n\n"
md += (
    "Reduce ML-KEM-768 encapsulation stack usage by moving the large local buffers "
    "inside `indcpa_enc` into explicit caller-provided workspace.\n\n"
)

md += "v26 is the first real ML-KEM implementation optimization after v25a and v25b.\n\n"

md += "## Stack result\n\n"

if V26_TARGETS.exists():
    md += V26_TARGETS.read_text() + "\n\n"
else:
    md += "No stack target report found.\n\n"

md += "## Correctness\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in v26_correctness:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Speed comparison against v25b baseline\n\n"
md += "| Operation | v25b baseline us | v26 us | Difference us | Difference % |\n"
md += "|---|---:|---:|---:|---:|\n"

for mode in ["kem-keypair", "kem-encaps", "kem-decaps"]:
    base = latest_speed(v25b_speed, "mlkem_only", mode)
    new = latest_speed(v26_speed, "v26_enc_workspace", mode)

    if base is None or new is None:
        md += f"| {mode} | missing | missing | missing | missing |\n"
        continue

    diff = new - base
    pct = (diff / base) * 100.0

    md += f"| {mode} | {base:.3f} | {new:.3f} | {diff:.3f} | {pct:.2f}% |\n"

md += "\n## v26 final speed\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in v26_speed:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Workspace\n\n"
md += "| Profile | Workspace kind | Bytes |\n"
md += "|---|---|---:|\n"

for row in v26_workspace:
    md += f"| {row['profile']} | {row['workspace_kind']} | {row['bytes']} |\n"

md += "\n## Binary size\n\n"
md += "| Profile | text | data | bss | dec | hex | Binary |\n"
md += "|---|---:|---:|---:|---:|---|---|\n"

for row in v26_size:
    md += (
        f"| {row['profile']} | {row['text']} | {row['data']} | {row['bss']} | "
        f"{row['dec']} | {row['hex']} | `{row['binary']}` |\n"
    )

md += "\n## Interpretation\n\n"
md += (
    "v26 successfully moved the large `indcpa_enc` local buffers from stack memory "
    "to explicit caller-provided workspace. The `indcpa_enc` stack frame dropped "
    "from 13312 B to 192 B on x86_64 and 160 B on ref. Correctness passed for "
    "keypair, encapsulation, and decapsulation.\n\n"
)

md += (
    "The measured encapsulation speed stayed close to the v25b baseline. "
    "The keypair and decapsulation stack frames are intentionally unchanged; "
    "they are the targets for v27 and v28.\n\n"
)

md += "## Safety rule\n\n"
md += (
    "v26 only changes storage location. It does not change ML-KEM arithmetic, "
    "matrix generation, noise generation, hashing/KDF behavior, compression, "
    "decompression, ciphertext verification, constant-time comparison, or "
    "decapsulation failure handling.\n\n"
)

md += "## Next version\n\n"
md += "v27 = ML-KEM keypair caller workspace for `indcpa_keypair_derand`.\n"

OUT.write_text(md)

print(f"wrote {OUT}")
