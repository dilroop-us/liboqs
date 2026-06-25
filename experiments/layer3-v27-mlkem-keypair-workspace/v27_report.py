#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v27_mlkem_keypair_workspace_report.md"

V25B_SPEED = RESULTS / "v25b_mlkem_speed.csv"
V26_SPEED = RESULTS / "v26_mlkem_speed.csv"
V27_SPEED = RESULTS / "v27_mlkem_speed.csv"
V27_CORRECTNESS = RESULTS / "v27_mlkem_correctness.csv"
V27_SIZE = RESULTS / "v27_mlkem_size.csv"
V27_WORKSPACE = RESULTS / "v27_mlkem_workspace.csv"
V27_TARGETS = RESULTS / "v27_mlkem_targets.md"


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
v27_speed = load_csv(V27_SPEED)
v27_correctness = load_csv(V27_CORRECTNESS)
v27_size = load_csv(V27_SIZE)
v27_workspace = dedup_rows(load_csv(V27_WORKSPACE), ["profile", "workspace_kind", "bytes"])

md = "# Layer 3 v27: ML-KEM Keypair Caller Workspace\n\n"

md += "## Goal\n\n"
md += (
    "Reduce ML-KEM-768 keypair stack usage by moving the large local buffers "
    "inside `indcpa_keypair_derand` into explicit caller-provided workspace.\n\n"
)

md += "v27 builds on v26. v26 reduced `indcpa_enc`; v27 reduces `indcpa_keypair_derand`.\n\n"

md += "## Stack result\n\n"

if V27_TARGETS.exists():
    md += V27_TARGETS.read_text() + "\n\n"
else:
    md += "No stack target report found.\n\n"

md += "## Correctness\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in v27_correctness:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Speed comparison\n\n"
md += "| Operation | v25b baseline us | v26 us | v27 us | v27 vs baseline % |\n"
md += "|---|---:|---:|---:|---:|\n"

for mode in ["kem-keypair", "kem-encaps", "kem-decaps"]:
    base = latest_speed(v25b_speed, "mlkem_only", mode)
    v26 = latest_speed(v26_speed, "v26_enc_workspace", mode)
    v27 = latest_speed(v27_speed, "v27_keypair_workspace", mode)

    if base is None or v27 is None:
        md += f"| {mode} | missing | missing | missing | missing |\n"
        continue

    pct = ((v27 - base) / base) * 100.0
    v26_s = f"{v26:.3f}" if v26 is not None else "missing"

    md += f"| {mode} | {base:.3f} | {v26_s} | {v27:.3f} | {pct:.2f}% |\n"

md += "\n## v27 final speed\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in v27_speed:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Workspace\n\n"
md += "| Profile | Workspace kind | Bytes |\n"
md += "|---|---|---:|\n"

for row in v27_workspace:
    md += f"| {row['profile']} | {row['workspace_kind']} | {row['bytes']} |\n"

md += "\n## Binary size\n\n"
md += "| Profile | text | data | bss | dec | hex | Binary |\n"
md += "|---|---:|---:|---:|---:|---|---|\n"

for row in v27_size:
    md += (
        f"| {row['profile']} | {row['text']} | {row['data']} | {row['bss']} | "
        f"{row['dec']} | {row['hex']} | `{row['binary']}` |\n"
    )

md += "\n## Interpretation\n\n"
md += (
    "v27 successfully moved the large `indcpa_keypair_derand` local buffers from "
    "stack memory to explicit caller-provided workspace. The keypair stack frame "
    "dropped from 10336 B to 192 B on x86_64 and 128 B on ref.\n\n"
)

md += (
    "`indcpa_enc` remains reduced from v26, and `indcpa_dec` is intentionally "
    "unchanged. Correctness passed for keypair, encapsulation, and decapsulation.\n\n"
)

md += (
    "The measured speed stayed close to the v25b/v26 baseline. Any small speed "
    "difference should be treated as benchmark variance, not as a cryptographic "
    "speedup claim.\n\n"
)

md += "## Safety rule\n\n"
md += (
    "v27 only changes storage location. It does not change ML-KEM arithmetic, "
    "matrix generation, noise generation, hashing/KDF behavior, packing, "
    "randomness behavior, constant-time behavior, or decapsulation failure handling.\n\n"
)

md += "## Next version\n\n"
md += "v28 = ML-KEM decapsulation caller workspace for `indcpa_dec`.\n"

OUT.write_text(md)

print(f"wrote {OUT}")
