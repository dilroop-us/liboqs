#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v28_mlkem_dec_workspace_report.md"

V25B_SPEED = RESULTS / "v25b_mlkem_speed.csv"
V26_SPEED = RESULTS / "v26_mlkem_speed.csv"
V27_SPEED = RESULTS / "v27_mlkem_speed.csv"
V28_SPEED = RESULTS / "v28_mlkem_speed.csv"
V28_CORRECTNESS = RESULTS / "v28_mlkem_correctness.csv"
V28_SIZE = RESULTS / "v28_mlkem_size.csv"
V28_WORKSPACE = RESULTS / "v28_mlkem_workspace.csv"
V28_TARGETS = RESULTS / "v28_mlkem_targets.md"


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
v28_speed = load_csv(V28_SPEED)
v28_correctness = load_csv(V28_CORRECTNESS)
v28_size = load_csv(V28_SIZE)
v28_workspace = dedup_rows(load_csv(V28_WORKSPACE), ["profile", "workspace_kind", "bytes"])

md = "# Layer 3 v28: ML-KEM Decapsulation Caller Workspace\n\n"

md += "## Goal\n\n"
md += (
    "Reduce ML-KEM-768 decapsulation stack usage by moving the large local buffers "
    "inside `indcpa_dec` into explicit caller-provided workspace.\n\n"
)

md += (
    "v28 builds on v26 and v27. v26 reduced `indcpa_enc`, v27 reduced "
    "`indcpa_keypair_derand`, and v28 reduces `indcpa_dec`.\n\n"
)

md += "## Stack result\n\n"

if V28_TARGETS.exists():
    md += V28_TARGETS.read_text() + "\n\n"
else:
    md += "No stack target report found.\n\n"

md += "## Correctness\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in v28_correctness:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Speed comparison\n\n"
md += "| Operation | v25b baseline us | v26 us | v27 us | v28 us | v28 vs baseline % |\n"
md += "|---|---:|---:|---:|---:|---:|\n"

for mode in ["kem-keypair", "kem-encaps", "kem-decaps"]:
    base = latest_speed(v25b_speed, "mlkem_only", mode)
    v26 = latest_speed(v26_speed, "v26_enc_workspace", mode)
    v27 = latest_speed(v27_speed, "v27_keypair_workspace", mode)
    v28 = latest_speed(v28_speed, "v28_dec_workspace", mode)

    if base is None or v28 is None:
        md += f"| {mode} | missing | missing | missing | missing | missing |\n"
        continue

    pct = ((v28 - base) / base) * 100.0

    v26_s = f"{v26:.3f}" if v26 is not None else "missing"
    v27_s = f"{v27:.3f}" if v27 is not None else "missing"

    md += f"| {mode} | {base:.3f} | {v26_s} | {v27_s} | {v28:.3f} | {pct:.2f}% |\n"

md += "\n## v28 final speed\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in v28_speed:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Workspace\n\n"
md += "| Profile | Workspace kind | Bytes |\n"
md += "|---|---|---:|\n"

for row in v28_workspace:
    md += f"| {row['profile']} | {row['workspace_kind']} | {row['bytes']} |\n"

md += "\n## Binary size\n\n"
md += "| Profile | text | data | bss | dec | hex | Binary |\n"
md += "|---|---:|---:|---:|---:|---|---|\n"

for row in v28_size:
    md += (
        f"| {row['profile']} | {row['text']} | {row['data']} | {row['bss']} | "
        f"{row['dec']} | {row['hex']} | `{row['binary']}` |\n"
    )

md += "\n## Interpretation\n\n"
md += (
    "v28 is successful if `indcpa_dec` stack usage is strongly reduced, "
    "`indcpa_enc` remains low from v26, `indcpa_keypair_derand` remains low "
    "from v27, correctness passes, and decapsulation speed remains close to "
    "the v25b/v27 baseline.\n\n"
)

md += (
    "After v28, the main ML-KEM IND-CPA stack frames have all been converted "
    "from large local stack usage to explicit caller-provided workspace.\n\n"
)

md += "## Safety rule\n\n"
md += (
    "v28 only changes storage location. It does not change ciphertext unpacking, "
    "secret-key unpacking, polynomial arithmetic, compression/decompression, "
    "message conversion, hashing/KDF behavior, constant-time behavior, "
    "or decapsulation failure handling.\n\n"
)

md += "## Next version\n\n"
md += "v29 = compact ML-KEM lifecycle workspace.\n"

OUT.write_text(md)

print(f"wrote {OUT}")
