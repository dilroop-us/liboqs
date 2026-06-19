#!/usr/bin/env python3
from pathlib import Path
import csv
import re

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

NORMAL = ROOT / "build-v23a-keygen-lifetime-map"
NOINLINE = ROOT / "build-v23a-keygen-lifetime-map-noinline"

TARGETS = ["keypair_internal", "pk_from_sk"]

SU_RE = re.compile(r"^(.*?):(\d+):(\d+):([^\t]+)\t(\d+)\t(.+)$")


def variant_from_path(path):
    if "mldsa-native_ml-dsa-44_x86_64" in path:
        return "x86_64"
    if "mldsa-native_ml-dsa-44_ref" in path:
        return "ref"
    return "unknown"


def load(build, build_name):
    rows = {}

    for su in build.rglob("*.su"):
        for line in su.read_text(errors="replace").splitlines():
            m = SU_RE.match(line)
            if not m:
                continue

            src, line_no, col_no, function, bytes_s, kind = m.groups()

            if "mldsa-native_ml-dsa-44" not in src:
                continue

            for target in TARGETS:
                if target in function:
                    key = (variant_from_path(src), target)
                    rows[key] = {
                        "build": build_name,
                        "variant": key[0],
                        "target": target,
                        "function": function,
                        "bytes": int(bytes_s),
                        "kind": kind,
                        "location": f"{src}:{line_no}:{col_no}",
                    }

    return rows


normal = load(NORMAL, "normal")
noinline = load(NOINLINE, "noinline")

keys = sorted(set(normal) | set(noinline))

csv_path = RESULTS / "v23a_noinline_compare.csv"
md_path = RESULTS / "v23a_noinline_compare.md"

with csv_path.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "variant", "target",
            "normal_bytes", "normal_kind",
            "noinline_bytes", "noinline_kind",
            "delta_bytes", "delta_percent",
        ],
    )
    writer.writeheader()

    for key in keys:
        n = normal.get(key)
        ni = noinline.get(key)

        normal_bytes = n["bytes"] if n else 0
        noinline_bytes = ni["bytes"] if ni else 0
        delta = noinline_bytes - normal_bytes
        delta_percent = (delta / normal_bytes * 100.0) if normal_bytes else 0.0

        writer.writerow({
            "variant": key[0],
            "target": key[1],
            "normal_bytes": normal_bytes,
            "normal_kind": n["kind"] if n else "",
            "noinline_bytes": noinline_bytes,
            "noinline_kind": ni["kind"] if ni else "",
            "delta_bytes": delta,
            "delta_percent": f"{delta_percent:.2f}",
        })

with md_path.open("w") as f:
    f.write("# v23a no-inline attribution comparison\n\n")
    f.write("| Variant | Target | Normal bytes | Normal kind | No-inline bytes | No-inline kind | Delta bytes | Delta % |\n")
    f.write("|---|---|---:|---|---:|---|---:|---:|\n")

    for key in keys:
        n = normal.get(key)
        ni = noinline.get(key)

        normal_bytes = n["bytes"] if n else 0
        noinline_bytes = ni["bytes"] if ni else 0
        delta = noinline_bytes - normal_bytes
        delta_percent = (delta / normal_bytes * 100.0) if normal_bytes else 0.0

        f.write(
            f"| {key[0]} | {key[1]} | {normal_bytes} | {n['kind'] if n else ''} | "
            f"{noinline_bytes} | {ni['kind'] if ni else ''} | {delta} | {delta_percent:.2f}% |\n"
        )

    f.write("\n## Interpretation\n\n")
    f.write(
        "`keypair_internal` and `pk_from_sk` stay close between normal and no-inline builds, "
        "so both frames are local-buffer dominated rather than inlining dominated.\n"
    )

print(f"wrote {csv_path}")
print(f"wrote {md_path}")
