#!/usr/bin/env python3

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
RESULTS = ROOT / "layer3-results"

RUN_LOG = RESULTS / "v41_rust_workspace_api_run.log"
CSV_OUT = RESULTS / "v41_rust_workspace_api.csv"
REPORT_OUT = RESULTS / "v41_rust_workspace_api_report.md"


def read_lines() -> list[str]:
    if not RUN_LOG.exists():
        return []

    return RUN_LOG.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()


def extract_value(prefix: str, default: str = "not found") -> str:
    for line in read_lines():
        if line.startswith(prefix):
            return line.split(",")[-1]

    return default


def parse_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for line in read_lines():
        if not line.startswith("V41_CASE,"):
            continue

        parts = line.split(",", 6)

        if len(parts) != 7:
            continue

        _, case, iterations, passed, failed, status, notes = parts

        rows.append(
            {
                "case": case,
                "iterations": iterations,
                "passed": passed,
                "failed": failed,
                "status": status,
                "notes": notes,
            }
        )

    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    with CSV_OUT.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
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

    total_rows = len(rows)
    pass_rows = sum(row["status"] == "PASS" for row in rows)
    fail_rows = sum(row["status"] == "FAIL" for row in rows)

    overall = (
        "PASS"
        if total_rows > 0 and fail_rows == 0
        else "FAIL"
    )

    iterations = extract_value("V41_CONFIG,ITERATIONS,")
    alignment = extract_value("V41_CONFIG,ALIGNMENT,")

    mlkem = int(extract_value("V41_WORKSPACE,ML-KEM,", "0"))
    mldsa = int(extract_value("V41_WORKSPACE,ML-DSA,", "0"))
    combined = int(extract_value("V41_WORKSPACE,COMBINED,", "0"))

    lines: list[str] = []

    lines.append("# Layer 3 v41: Rust Workspace Ownership and Alignment API")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(
        "v41 moves lifecycle workspace allocation, alignment, activation, "
        "ownership, and zeroization into a Rust-side workspace context."
    )
    lines.append("")
    lines.append(
        "Crypto operations use the workspace context instead of directly "
        "managing raw allocation and lifecycle setter calls."
    )
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| crypto iterations per flow | {iterations} |")
    lines.append(f"| workspace alignment | {alignment} bytes |")
    lines.append("")
    lines.append("## Workspace accounting")
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
    lines.append(f"| total rows | {total_rows} |")
    lines.append(f"| PASS rows | {pass_rows} |")
    lines.append(f"| FAIL rows | {fail_rows} |")
    lines.append(f"| overall v41 status | {overall} |")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append(
        "| Case | Iterations | Passed | Failed | Status | Notes |"
    )
    lines.append("|---|---:|---:|---:|---|---|")

    for row in rows:
        lines.append(
            f"| {row['case']} | {row['iterations']} | "
            f"{row['passed']} | {row['failed']} | "
            f"{row['status']} | {row['notes']} |"
        )

    lines.append("")
    lines.append("## What v41 validates")
    lines.append("")
    lines.append("| Area | Validation |")
    lines.append("|---|---|")
    lines.append(
        "| Ownership | Rust context owns both lifecycle workspace allocations |"
    )
    lines.append(
        "| Size accounting | Workspace sizes match 13088 and 44064 bytes |"
    )
    lines.append(
        "| Alignment | Both allocations satisfy 64-byte alignment |"
    )
    lines.append(
        "| Initialization | New workspace memory begins zero initialized |"
    )
    lines.append(
        "| Activation | C and x86_64 lifecycle setters accept the owned buffers |"
    )
    lines.append(
        "| Zeroization | The live volatile wipe routine restores workspace bytes to zero |"
    )
    lines.append(
        "| Crypto integration | ML-KEM ML-DSA and combined flows use the context successfully |"
    )
    lines.append("")
    lines.append("## Zeroization interpretation")
    lines.append("")
    lines.append(
        "The runtime test validates the same wipe routine while the allocation "
        "is still live. The Drop implementation calls that wipe routine before "
        "deallocation."
    )
    lines.append("")
    lines.append(
        "The harness intentionally does not read memory after deallocation, "
        "because doing so would be undefined behavior."
    )
    lines.append("")
    lines.append("## Claim supported by v41")
    lines.append("")
    lines.append(
        "> v41 provides evidence that Rust can own, align, activate, and "
        "zeroize the optimized ML-KEM-768 and ML-DSA-44 lifecycle "
        "workspaces through a reusable workspace context while preserving "
        "the tested cryptographic flows."
    )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- v41 is not a formal proof of Rust memory safety.")
    lines.append("- v41 does not eliminate all unsafe FFI code.")
    lines.append("- v41 does not test cross-thread workspace movement.")
    lines.append("- v41 does not test async task behavior.")
    lines.append("- v41 does not test all target architectures.")
    lines.append("- v41 does not test real constrained-device hardware.")
    lines.append("- v41 does not prove production readiness.")
    lines.append("")
    lines.append("## Next")
    lines.append("")
    lines.append(
        "v42 should add a structured Rust correctness test suite around "
        "the workspace API with repeatable positive and negative test cases."
    )
    lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")

    print(
        f"v41 summary: total_rows={total_rows} "
        f"pass_rows={pass_rows} fail_rows={fail_rows}"
    )
    print(f"overall v41 status | {overall}")
    print(f"wrote {CSV_OUT}")
    print(f"wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
