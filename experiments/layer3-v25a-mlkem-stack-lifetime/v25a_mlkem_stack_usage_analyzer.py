#!/usr/bin/env python3
from pathlib import Path
import csv
import sys

if len(sys.argv) != 4:
    raise SystemExit(
        "usage: v25a_mlkem_stack_usage_analyzer.py <build-dir> <profile-name> <results-dir>"
    )

BUILD = Path(sys.argv[1]).resolve()
PROFILE = sys.argv[2]
RESULTS = Path(sys.argv[3]).resolve()
RESULTS.mkdir(parents=True, exist_ok=True)

OUT_CSV = RESULTS / f"v25a_{PROFILE}_mlkem_stack_usage.csv"
OUT_TOP = RESULTS / f"v25a_{PROFILE}_mlkem_top_stack_usage.md"
OUT_TARGETS = RESULTS / f"v25a_{PROFILE}_mlkem_targets.md"

TARGET_SUBSTRINGS = [
    "indcpa_keypair_derand",
    "indcpa_enc",
    "indcpa_dec",
    "keypair_derand",
    "keypair",
    "encaps",
    "decaps",
]


def detect_variant(text: str) -> str:
    if "mlkem-native_ml-kem-768_x86_64" in text or "MLKEM768_X86_64" in text:
        return "x86_64"

    if "mlkem-native_ml-kem-768_ref" in text or "MLKEM768_C" in text:
        return "ref"

    return "unknown"


def parse_su_line(path: Path, line: str):
    parts = line.strip().split("\t")

    if len(parts) < 3:
        return None

    locfunc = parts[0]
    bytes_s = parts[1]
    kind = parts[2]

    try:
        bytes_i = int(bytes_s)
    except ValueError:
        return None

    if ":" not in locfunc:
        return None

    location, function = locfunc.rsplit(":", 1)

    full = str(path) + " " + locfunc + " " + function

    if "ml_kem" not in full and "MLKEM" not in full and "mlkem" not in full:
        return None

    return {
        "profile": PROFILE,
        "variant": detect_variant(full),
        "bytes": bytes_i,
        "kind": kind,
        "function": function,
        "location": location,
        "su_file": str(path),
    }


rows = []

for su in BUILD.rglob("*.su"):
    for line in su.read_text(errors="replace").splitlines():
        parsed = parse_su_line(su, line)

        if parsed is not None:
            rows.append(parsed)

rows.sort(key=lambda r: r["bytes"], reverse=True)

with OUT_CSV.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "profile",
            "variant",
            "bytes",
            "kind",
            "function",
            "location",
            "su_file",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

top_rows = rows[:60]

md = f"# v25a top ML-KEM stack-usage functions: {PROFILE}\n\n"
md += "| Rank | Variant | Bytes | Kind | Function | Location |\n"
md += "|---:|---|---:|---|---|---|\n"

for i, r in enumerate(top_rows, 1):
    md += (
        f"| {i} | {r['variant']} | {r['bytes']} | {r['kind']} | "
        f"`{r['function']}` | `{r['location']}` |\n"
    )

OUT_TOP.write_text(md)

target_rows = []

for r in rows:
    fn = r["function"]

    for target in TARGET_SUBSTRINGS:
        if target in fn:
            target_rows.append(
                {
                    "target": target,
                    **r,
                }
            )
            break

target_rows.sort(key=lambda r: (r["variant"], r["target"], -r["bytes"]))

md = "# v25a target ML-KEM stack frames\n\n"
md += "| Variant | Target | Bytes | Kind | Function | Location |\n"
md += "|---|---|---:|---|---|---|\n"

for r in target_rows:
    md += (
        f"| {r['variant']} | {r['target']} | {r['bytes']} | {r['kind']} | "
        f"`{r['function']}` | `{r['location']}` |\n"
    )

OUT_TARGETS.write_text(md)

print(f"wrote {OUT_CSV}")
print(f"wrote {OUT_TOP}")
print(f"wrote {OUT_TARGETS}")
print(f"rows: {len(rows)}")
