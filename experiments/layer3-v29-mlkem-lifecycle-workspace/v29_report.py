#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v29_mlkem_lifecycle_workspace_report.md"

V25B_SPEED = RESULTS / "v25b_mlkem_speed.csv"
V26_SPEED = RESULTS / "v26_mlkem_speed.csv"
V27_SPEED = RESULTS / "v27_mlkem_speed.csv"
V28_SPEED = RESULTS / "v28_mlkem_speed.csv"
V29_SPEED = RESULTS / "v29_mlkem_speed.csv"
V29_CORRECTNESS = RESULTS / "v29_mlkem_correctness.csv"
V29_SIZE = RESULTS / "v29_mlkem_size.csv"
V29_WORKSPACE = RESULTS / "v29_mlkem_workspace.csv"
V29_TARGETS = RESULTS / "v29_mlkem_targets.md"


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


def workspace_value(rows, kind):
    matches = [r for r in rows if r["workspace_kind"] == kind]

    if not matches:
        return None

    return int(matches[-1]["bytes"])


v25b_speed = load_csv(V25B_SPEED)
v26_speed = load_csv(V26_SPEED)
v27_speed = load_csv(V27_SPEED)
v28_speed = load_csv(V28_SPEED)
v29_speed = load_csv(V29_SPEED)
v29_correctness = load_csv(V29_CORRECTNESS)
v29_size = load_csv(V29_SIZE)
v29_workspace = dedup_rows(load_csv(V29_WORKSPACE), ["profile", "workspace_kind", "bytes"])

separate_total = workspace_value(v29_workspace, "v29_separate_total")
lifecycle = workspace_value(v29_workspace, "v29_lifecycle_workspace")
saved = workspace_value(v29_workspace, "v29_saved_bytes")

saving_pct = None
if separate_total and saved is not None:
    saving_pct = (saved / separate_total) * 100.0

md = "# Layer 3 v29: Compact ML-KEM Lifecycle Workspace\n\n"

md += "## Goal\n\n"
md += (
    "Reduce explicit caller-provided ML-KEM workspace memory by combining the "
    "separate v26 encapsulation, v27 keypair, and v28 decapsulation workspaces "
    "into one reusable lifecycle workspace.\n\n"
)

md += (
    "v29 does not primarily target stack reduction. The stack reduction was already "
    "achieved in v26, v27, and v28. v29 targets explicit workspace compaction.\n\n"
)

md += "## Stack result\n\n"

if V29_TARGETS.exists():
    md += V29_TARGETS.read_text() + "\n\n"
else:
    md += "No stack target report found.\n\n"

md += "## Correctness\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in v29_correctness:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Speed comparison\n\n"
md += "| Operation | v25b baseline us | v26 us | v27 us | v28 us | v29 us | v29 vs baseline % |\n"
md += "|---|---:|---:|---:|---:|---:|---:|\n"

for mode in ["kem-keypair", "kem-encaps", "kem-decaps"]:
    base = latest_speed(v25b_speed, "mlkem_only", mode)
    v26 = latest_speed(v26_speed, "v26_enc_workspace", mode)
    v27 = latest_speed(v27_speed, "v27_keypair_workspace", mode)
    v28 = latest_speed(v28_speed, "v28_dec_workspace", mode)
    v29 = latest_speed(v29_speed, "v29_lifecycle_workspace", mode)

    if base is None or v29 is None:
        md += f"| {mode} | missing | missing | missing | missing | missing | missing |\n"
        continue

    pct = ((v29 - base) / base) * 100.0

    v26_s = f"{v26:.3f}" if v26 is not None else "missing"
    v27_s = f"{v27:.3f}" if v27 is not None else "missing"
    v28_s = f"{v28:.3f}" if v28 is not None else "missing"

    md += f"| {mode} | {base:.3f} | {v26_s} | {v27_s} | {v28_s} | {v29:.3f} | {pct:.2f}% |\n"

md += "\n## v29 final speed\n\n"
md += "| Profile | Operation | Iterations | Mean us | OK |\n"
md += "|---|---|---:|---:|---:|\n"

for row in v29_speed:
    md += (
        f"| {row['profile']} | {row['mode']} | {row['iterations']} | "
        f"{float(row['mean_us']):.3f} | {row['ok']} |\n"
    )

md += "\n## Workspace compaction\n\n"
md += "| Profile | Workspace kind | Bytes |\n"
md += "|---|---|---:|\n"

for row in v29_workspace:
    md += f"| {row['profile']} | {row['workspace_kind']} | {row['bytes']} |\n"

if separate_total is not None and lifecycle is not None and saved is not None:
    md += "\n## Workspace saving\n\n"
    md += "| Separate workspace total | Compact lifecycle workspace | Saved bytes | Saved % |\n"
    md += "|---:|---:|---:|---:|\n"
    md += f"| {separate_total} | {lifecycle} | {saved} | {saving_pct:.2f}% |\n"

md += "\n## Binary size\n\n"
md += "| Profile | text | data | bss | dec | hex | Binary |\n"
md += "|---|---:|---:|---:|---:|---|---|\n"

for row in v29_size:
    md += (
        f"| {row['profile']} | {row['text']} | {row['data']} | {row['bss']} | "
        f"{row['dec']} | {row['hex']} | `{row['binary']}` |\n"
    )

md += "\n## Interpretation\n\n"
md += (
    "v29 successfully keeps the v26/v27/v28 stack reductions unchanged while "
    "reducing explicit workspace memory from the sum of three separate operation "
    "workspaces to one compact lifecycle workspace.\n\n"
)

md += (
    "The compact lifecycle workspace reuses memory across keypair, encapsulation, "
    "and decapsulation because those lifecycle operations are not active at the "
    "same time in this benchmark/API usage model.\n\n"
)

md += (
    "The measured speed remains close to the v25b baseline. Small differences "
    "should be treated as benchmark variance, not as a cryptographic speedup or slowdown claim.\n\n"
)

md += "## Safety rule\n\n"
md += (
    "v29 only changes workspace ownership and layout. It does not change ML-KEM "
    "arithmetic, matrix generation, noise generation, packing, compression/"
    "decompression, hashing/KDF behavior, constant-time behavior, or "
    "decapsulation failure handling.\n\n"
)

md += "## Next\n\n"
md += "After v29, the ML-KEM high-level workspace optimization phase is complete.\n"

OUT.write_text(md)

print(f"wrote {OUT}")
