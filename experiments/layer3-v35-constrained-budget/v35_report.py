#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
RESULTS = ROOT / "layer3-results"

CSV_IN = RESULTS / "v35_constrained_budget.csv"
SIZE_CSV = RESULTS / "v35_size.csv"
STACK_CSV = RESULTS / "v35_stack_usage.csv"

RUN_LOG = RESULTS / "v35_constrained_budget_run.log"
TIME_LOG = RESULTS / "v35_time.log"
REPORT_OUT = RESULTS / "v35_constrained_budget_report.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def extract_workspace_sizes() -> tuple[int, int, int]:
    text = RUN_LOG.read_text(encoding="utf-8", errors="replace")

    mlkem = 0
    mldsa = 0
    combined = 0

    for line in text.splitlines():
        if line.startswith("V35_WORKSPACE,ML-KEM,"):
            mlkem = int(line.split(",")[2])
        elif line.startswith("V35_WORKSPACE,ML-DSA,"):
            mldsa = int(line.split(",")[2])
        elif line.startswith("V35_WORKSPACE,COMBINED,"):
            combined = int(line.split(",")[2])

    return mlkem, mldsa, combined


def extract_time_value(label: str) -> str:
    if not TIME_LOG.exists():
        return "not found"

    text = TIME_LOG.read_text(encoding="utf-8", errors="replace")
    pattern = re.escape(label) + r":\s+(.+)"
    m = re.search(pattern, text)
    return m.group(1).strip() if m else "not found"


def main() -> None:
    rows = read_csv(CSV_IN)
    size_rows = read_csv(SIZE_CSV)
    stack_rows = read_csv(STACK_CSV)

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = sum(1 for r in rows if r["status"] == "FAIL")
    overall = "PASS" if failed == 0 and total > 0 else "FAIL"

    mlkem, mldsa, combined = extract_workspace_sizes()

    lines: list[str] = []

    lines.append("# Layer 3 v35: Constrained-Device Memory Budget Validation")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("v35 evaluates the optimized lifecycle-workspace build under constrained-device-style resource checks.")
    lines.append("")
    lines.append("This is a host-side Raspberry-Pi-style budget validation. It does not claim actual Raspberry Pi runtime validation unless the harness is run on a Raspberry Pi.")
    lines.append("")
    lines.append("The optimized build uses:")
    lines.append("")
    lines.append("- ML-KEM-768 with v29 lifecycle workspace")
    lines.append("- ML-DSA-44 with v24 lifecycle workspace")
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
    lines.append(f"| PASS rows | {passed} |")
    lines.append(f"| FAIL rows | {failed} |")
    lines.append(f"| overall v35 status | {overall} |")
    lines.append("")
    lines.append("## Budget and correctness results")
    lines.append("")
    lines.append("| Category | Name | Value | Budget | Iterations | Passed | Failed | Status | Notes |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|---|")

    for r in rows:
        lines.append(
            f"| {r['category']} | {r['name']} | {r['value']} | {r['budget']} | {r['iterations']} | {r['passed']} | {r['failed']} | {r['status']} | {r['notes']} |"
        )

    lines.append("")
    lines.append("## Binary and runtime size details")
    lines.append("")
    lines.append("| Metric | Value | Budget | Status |")
    lines.append("|---|---:|---:|---|")

    for r in size_rows:
        lines.append(f"| {r['metric']} | {r['value']} | {r['budget']} | {r['status']} |")

    lines.append("")
    lines.append("## Runtime memory")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Maximum resident set size | {extract_time_value('Maximum resident set size (kbytes)')} kB |")
    lines.append(f"| User time | {extract_time_value('User time (seconds)')} s |")
    lines.append(f"| System time | {extract_time_value('System time (seconds)')} s |")
    lines.append(f"| Exit status | {extract_time_value('Exit status')} |")
    lines.append("")
    lines.append("## Top static stack-usage entries")
    lines.append("")
    lines.append("| Rank | Bytes | Kind | Function | File |")
    lines.append("|---:|---:|---|---|---|")

    for i, r in enumerate(stack_rows[:20], 1):
        func = r["function"].replace("|", "\\|")
        file_name = r["file"].replace("|", "\\|")
        lines.append(f"| {i} | {r['bytes']} | {r['kind']} | `{func}` | `{file_name}` |")

    lines.append("")
    lines.append("## What v35 checks")
    lines.append("")
    lines.append("| Area | Check |")
    lines.append("|---|---|")
    lines.append("| Workspace budget | ML-KEM, ML-DSA, and combined explicit workspace fit under configured budgets |")
    lines.append("| Binary size | static archive and harness binary size are recorded and budget checked |")
    lines.append("| Stack usage | compiler `.su` files are scanned and the largest static stack entries are reported |")
    lines.append("| Runtime RSS | `/usr/bin/time -v` maximum resident set size is recorded and budget checked |")
    lines.append("| Correctness | ML-KEM, ML-DSA, and combined KEM-transcript-signature flows are re-run |")
    lines.append("")
    lines.append("## Claims supported by v35")
    lines.append("")
    lines.append("| Claim | Status |")
    lines.append("|---|---|")
    lines.append("| optimized explicit workspace fits under the constrained workspace budget | supported if PASS |")
    lines.append("| size-focused minimal build remains correct for tested ML-KEM and ML-DSA flows | supported if PASS |")
    lines.append("| observed runtime RSS fits under configured host-side constrained-device budget | supported if PASS |")
    lines.append("| largest observed static stack-usage entry fits under configured stack budget | supported if PASS |")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- v35 is not actual Raspberry Pi validation unless run on Raspberry Pi hardware.")
    lines.append("- v35 does not prove constant-time behavior.")
    lines.append("- v35 does not prove formal memory safety.")
    lines.append("- v35 does not prove thread/TLS safety.")
    lines.append("- v35 does not test Rust FFI.")
    lines.append("- v35 does not measure energy usage or thermal throttling.")
    lines.append("")
    lines.append("## Next")
    lines.append("")
    lines.append("v36 should perform timing/constant-time-style leakage checks, for example using repeated timing distributions or dudect-style experiments.")
    lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
