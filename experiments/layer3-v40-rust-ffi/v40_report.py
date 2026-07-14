#!/usr/bin/env python3

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
RESULTS = ROOT / "layer3-results"

RUN_LOG = RESULTS / "v40_rust_ffi_run.log"
CSV_OUT = RESULTS / "v40_rust_ffi.csv"
REPORT_OUT = RESULTS / "v40_rust_ffi_report.md"


def extract_config(name: str) -> str:
    if not RUN_LOG.exists():
        return "not found"

    prefix = f"V40_CONFIG,{name},"
    for line in RUN_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line.split(",", 2)[2]
    return "not found"


def extract_workspace(name: str) -> int:
    if not RUN_LOG.exists():
        return 0

    prefix = f"V40_WORKSPACE,{name},"
    for line in RUN_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return int(line.split(",")[2])
    return 0


def parse_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    if not RUN_LOG.exists():
        return rows

    for line in RUN_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("V40_CASE,"):
            continue

        parts = line.split(",", 6)
        if len(parts) != 7:
            continue

        _tag, case, iterations, passed, failed, status, notes = parts

        rows.append({
            "case": case,
            "iterations": iterations,
            "passed": passed,
            "failed": failed,
            "status": status,
            "notes": notes,
        })

    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case",
                "iterations",
                "passed",
                "failed",
                "status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = parse_rows()
    write_csv(rows)

    total = len(rows)
    passed_rows = sum(1 for r in rows if r["status"] == "PASS")
    failed_rows = sum(1 for r in rows if r["status"] == "FAIL")

    overall = "PASS" if total > 0 and failed_rows == 0 else "FAIL"

    iterations = extract_config("ITERATIONS")

    mlkem = extract_workspace("ML-KEM")
    mldsa = extract_workspace("ML-DSA")
    combined = extract_workspace("COMBINED")

    lines: list[str] = []

    lines.append("# Layer 3 v40: Rust FFI / Integration Validation")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("v40 validates that Rust can link against the optimized liboqs build, configure Rust-owned aligned lifecycle workspaces through FFI, and execute tested ML-KEM, ML-DSA, and combined flows.")
    lines.append("")
    lines.append("The optimized build uses:")
    lines.append("")
    lines.append("- ML-KEM-768 with v29 lifecycle workspace")
    lines.append("- ML-DSA-44 with v24 lifecycle workspace")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| iterations per case | {iterations} |")
    lines.append("")
    lines.append("## Workspace sizes")
    lines.append("")
    lines.append("| Scheme | Bytes | KiB |")
    lines.append("|---|---:|---:|")
    lines.append(f"| ML-KEM-768 | {mlkem} | {mlkem / 1024:.2f} |")
    lines.append(f"| ML-DSA-44 | {mldsa} | {mldsa / 1024:.2f} |")
    lines.append(f"| Combined | {combined} | {combined / 1024:.2f} |")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| total rows | {total} |")
    lines.append(f"| PASS rows | {passed_rows} |")
    lines.append(f"| FAIL rows | {failed_rows} |")
    lines.append(f"| overall v40 status | {overall} |")
    lines.append("")
    lines.append("## Rust FFI results")
    lines.append("")
    lines.append("| Case | Iterations | Passed | Failed | Status | Notes |")
    lines.append("|---|---:|---:|---:|---|---|")

    for r in rows:
        lines.append(
            f"| {r['case']} | {r['iterations']} | {r['passed']} | {r['failed']} | {r['status']} | {r['notes']} |"
        )

    lines.append("")
    lines.append("## What v40 checks")
    lines.append("")
    lines.append("| Area | Check |")
    lines.append("|---|---|")
    lines.append("| Rust linking | Rust binary links against optimized static liboqs build |")
    lines.append("| Rust FFI | Rust calls OQS KEM/SIG APIs through extern C declarations |")
    lines.append("| Workspace ownership | Rust allocates 64-byte aligned caller-owned lifecycle workspaces |")
    lines.append("| Workspace setup | Rust calls ML-KEM and ML-DSA lifecycle workspace setters |")
    lines.append("| ML-KEM correctness | keypair, encaps, decaps, shared-secret equality |")
    lines.append("| ML-DSA correctness | keypair, sign, verify, modified message/signature rejection |")
    lines.append("| Combined flow | ML-KEM transcript construction and ML-DSA signature verification |")
    lines.append("")
    lines.append("## Claims supported by v40")
    lines.append("")
    lines.append("| Claim | Status |")
    lines.append("|---|---|")
    lines.append("| Rust can link against the optimized liboqs build | supported if PASS |")
    lines.append("| Rust-owned aligned lifecycle workspaces can be configured through FFI | supported if PASS |")
    lines.append("| Tested ML-KEM, ML-DSA, and combined Rust FFI flows pass | supported if PASS |")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- v40 does not prove full Rust safety.")
    lines.append("- v40 does not prove complete FFI safety.")
    lines.append("- v40 does not test async/threading safety; that belongs to a later step.")
    lines.append("- v40 does not test all target platforms.")
    lines.append("- v40 does not test real constrained-device hardware.")
    lines.append("- v40 does not prove production readiness.")
    lines.append("")
    lines.append("## Next")
    lines.append("")
    lines.append("v41 should build a cleaner Rust workspace ownership/alignment API so raw unsafe FFI calls are not spread across the Rust integration layer.")
    lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {CSV_OUT}")
    print(f"wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
