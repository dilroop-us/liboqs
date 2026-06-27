#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"
BUILD = ROOT / "build-v28-mlkem-dec-workspace"
OUT = ROOT / "layer3-results/v28_mlkem_targets.md"

PREVIOUS = {
    ("x86_64", "indcpa_keypair_derand"): 192,
    ("ref", "indcpa_keypair_derand"): 128,
    ("x86_64", "indcpa_enc"): 192,
    ("ref", "indcpa_enc"): 160,
    ("x86_64", "indcpa_dec"): 4992,
    ("ref", "indcpa_dec"): 4992,
}

TARGETS = [
    "indcpa_keypair_derand",
    "indcpa_enc",
    "indcpa_dec",
]


def detect_variant(text: str) -> str:
    if "MLKEM768_X86_64" in text or "mlkem-native_ml-kem-768_x86_64" in text:
        return "x86_64"
    if "MLKEM768_C" in text or "mlkem-native_ml-kem-768_ref" in text:
        return "ref"
    return "unknown"


def target_of(function: str):
    for target in TARGETS:
        if target in function:
            return target
    return None


rows = {}

for su in BUILD.rglob("*.su"):
    for line in su.read_text(errors="replace").splitlines():
        parts = line.strip().split()

        if len(parts) < 3:
            continue

        locfunc = parts[0]

        try:
            stack_bytes = int(parts[1])
        except ValueError:
            continue

        kind = " ".join(parts[2:])

        if ":" not in locfunc:
            continue

        location, function = locfunc.rsplit(":", 1)
        target = target_of(function)

        if target is None:
            continue

        variant = detect_variant(function + " " + str(su) + " " + location)

        if variant == "unknown":
            continue

        rows[(variant, target)] = {
            "variant": variant,
            "target": target,
            "bytes": stack_bytes,
            "kind": kind,
            "function": function,
            "location": location,
        }


def reduction(prev, new):
    if prev == new:
        return "unchanged"
    pct = ((prev - new) / prev) * 100.0
    return f"{pct:.2f}%"


ordered = [
    ("x86_64", "indcpa_keypair_derand"),
    ("ref", "indcpa_keypair_derand"),
    ("x86_64", "indcpa_enc"),
    ("ref", "indcpa_enc"),
    ("x86_64", "indcpa_dec"),
    ("ref", "indcpa_dec"),
]

missing = [key for key in ordered if key not in rows]

if missing:
    raise SystemExit(f"missing stack rows: {missing}")

md = "# v28 target ML-KEM stack frames\n\n"
md += "| Variant | Function | Previous stack | v28 stack | Reduction |\n"
md += "|---|---|---:|---:|---:|\n"

for key in ordered:
    prev = PREVIOUS[key]
    new = rows[key]["bytes"]
    md += (
        f"| {key[0]} | `{key[1]}` | {prev} B | {new} B | "
        f"{reduction(prev, new)} |\n"
    )

md += "\n## Raw compiler symbols\n\n"
md += "| Variant | Function | Bytes | Kind | Location |\n"
md += "|---|---|---:|---|---|\n"

for key in ordered:
    row = rows[key]
    md += (
        f"| {row['variant']} | `{row['function']}` | {row['bytes']} | "
        f"{row['kind']} | `{row['location']}` |\n"
    )

md += "\n## Interpretation\n\n"
md += (
    "v28 moves the large `indcpa_dec` local buffers out of the stack and into "
    "explicit caller-provided workspace.\n\n"
)

md += (
    "`indcpa_enc` remains reduced from v26. `indcpa_keypair_derand` remains "
    "reduced from v27. After v28, the three main ML-KEM IND-CPA stack frames "
    "should all be small.\n"
)

OUT.write_text(md)

print(f"wrote {OUT}")
