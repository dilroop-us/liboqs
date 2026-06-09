#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path


def parse_su_line(line: str, su_file: Path):
    parts = line.strip().split("\t")
    if len(parts) < 2:
        return None

    loc_func = parts[0]
    size_raw = parts[1]
    kind = parts[2] if len(parts) >= 3 else ""

    try:
        size = int(size_raw)
    except ValueError:
        return None

    try:
        location, function = loc_func.rsplit(":", 1)
    except ValueError:
        location = loc_func
        function = ""

    return {
        "bytes": size,
        "kind": kind,
        "function": function,
        "location": location,
        "su_file": str(su_file),
    }


def is_mldsa_related(row: dict) -> bool:
    location = row.get("location", "").lower()
    function = row.get("function", "").lower()

    return (
        "/src/sig/ml_dsa/" in location
        or "mldsa" in function
        or "mld_" in function
    )


def source_variant(row: dict) -> str:
    location = row.get("location", "")
    if "mldsa-native_ml-dsa-44_x86_64" in location:
        return "x86_64"
    if "mldsa-native_ml-dsa-44_ref" in location:
        return "ref"
    return "other"


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: v15_stack_usage_analyzer.py <build_dir> <profile> <out_dir>", file=sys.stderr)
        return 2

    build_dir = Path(sys.argv[1]).expanduser().resolve()
    profile = sys.argv[2]
    out_dir = Path(sys.argv[3]).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for su_file in build_dir.rglob("*.su"):
        try:
            text = su_file.read_text(errors="replace")
        except OSError:
            continue

        for line in text.splitlines():
            row = parse_su_line(line, su_file)
            if row is None:
                continue
            if not is_mldsa_related(row):
                continue

            row["profile"] = profile
            row["variant"] = source_variant(row)
            rows.append(row)

    rows.sort(key=lambda r: r["bytes"], reverse=True)

    csv_path = out_dir / f"v15_{profile}_stack_usage.csv"
    top_path = out_dir / f"v15_{profile}_top_stack_usage.md"
    x86_top_path = out_dir / f"v15_{profile}_x86_64_top_stack_usage.md"

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["profile", "variant", "bytes", "kind", "function", "location", "su_file"],
        )
        writer.writeheader()
        writer.writerows(rows)

    def write_md(path: Path, title: str, selected_rows: list[dict]) -> None:
        with path.open("w") as f:
            f.write(f"# {title}\n\n")
            f.write("| Rank | Variant | Bytes | Kind | Function | Location |\n")
            f.write("|---:|---|---:|---|---|---|\n")
            for idx, row in enumerate(selected_rows[:40], 1):
                f.write(
                    f"| {idx} | {row['variant']} | {row['bytes']} | {row['kind']} | "
                    f"`{row['function']}` | `{row['location']}` |\n"
                )

    write_md(top_path, f"v15 top ML-DSA stack-usage functions: {profile}", rows)
    write_md(
        x86_top_path,
        f"v15 top ML-DSA x86_64 stack-usage functions: {profile}",
        [r for r in rows if r["variant"] == "x86_64"],
    )

    print(f"wrote {csv_path}")
    print(f"wrote {top_path}")
    print(f"wrote {x86_top_path}")
    print(f"rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
