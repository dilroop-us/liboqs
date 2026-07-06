#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
RESULTS = ROOT / "layer3-results"

CSV_IN = RESULTS / "v34_memory_safety.csv"
REPORT_OUT = RESULTS / "v34_memory_safety_report.md"
ASAN_LOG = RESULTS / "v34_asan_ubsan_run.log"
VALGRIND_LOG = RESULTS / "v34_valgrind_run.log"


def read_rows() -> list[dict[str, str]]:
    with CSV_IN.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def extract_workspace_sizes() -> tuple[int, int, int]:
    text = ASAN_LOG.read_text(encoding="utf-8", errors="replace")

    mlkem = 0
    mldsa = 0
    combined = 0

    for line in text.splitlines():
        if line.startswith("V34_WORKSPACE,ML-KEM,"):
            mlkem = int(line.split(",")[2])
        elif line.startswith("V34_WORKSPACE,ML-DSA,"):
            mldsa = int(line.split(",")[2])
        elif line.startswith("V34_WORKSPACE,COMBINED,"):
            combined = int(line.split(",")[2])

    return mlkem, mldsa, combined


def valgrind_error_summary() -> str:
    if not VALGRIND_LOG.exists():
        return "not found"

    text = VALGRIND_LOG.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"ERROR SUMMARY: .*", text)
    return matches[-1] if matches else "not found"


def main() -> None:
    rows = read_rows()

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = total - passed
    overall = "PASS" if failed == 0 and total > 0 else "FAIL"

    mlkem, mldsa, combined = extract_workspace_sizes()

    lines: list[str] = []

    lines.append("# Layer 3 v34: ASan/UBSan/Valgrind Memory-Safety Validation")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("v34 checks whether the optimized lifecycle-workspace build triggers sanitizer or Valgrind findings under representative ML-KEM, ML-DSA, and combined protocol-like flows.")
    lines.append("")
    lines.append("The optimized build uses:")
    lines.append("")
    lines.append("- ML-KEM-768 with v29 lifecycle workspace")
    lines.append("- ML-DSA-44 with v24 lifecycle workspace")
    lines.append("")
    lines.append("v34 does not add a new optimization. It validates memory-safety behavior of the existing optimized implementation.")
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
    lines.append(f"| overall v34 status | {overall} |")
    lines.append("")
    lines.append("## Tool results")
    lines.append("")
    lines.append("| Tool | Case | Iterations | Passed | Failed | Status | Notes |")
    lines.append("|---|---|---:|---:|---:|---|---|")

    for r in rows:
        lines.append(
            f"| {r['tool']} | {r['case']} | {r['iterations']} | {r['passed']} | {r['failed']} | {r['status']} | {r['notes']} |"
        )

    lines.append("")
    lines.append("## Valgrind summary")
    lines.append("")
    lines.append(f"```text\n{valgrind_error_summary()}\n```")
    lines.append("")
    lines.append("## What v34 checks")
    lines.append("")
    lines.append("| Area | Check |")
    lines.append("|---|---|")
    lines.append("| ASan | invalid reads/writes, use-after-free, double free, heap buffer overflow |")
    lines.append("| UBSan | undefined behavior such as invalid shifts, alignment issues, integer UB where instrumented |")
    lines.append("| Valgrind | invalid memory access, uninitialized-value use, definite/possible leaks, runtime memory errors |")
    lines.append("| ML-KEM flow | keypair, encaps, decaps, shared-secret equality |")
    lines.append("| ML-DSA flow | keypair, sign, verify, reject modified message, reject modified signature |")
    lines.append("| Combined flow | KEM transcript construction, ML-DSA signing, verification, negative transcript/signature checks |")
    lines.append("")
    lines.append("## Claims supported by v34")
    lines.append("")
    lines.append("| Claim | Status |")
    lines.append("|---|---|")
    lines.append("| optimized ML-KEM lifecycle-workspace flow produced no sanitizer findings in this harness | supported if PASS |")
    lines.append("| optimized ML-DSA lifecycle-workspace flow produced no sanitizer findings in this harness | supported if PASS |")
    lines.append("| optimized combined KEM transcript plus DSA signature flow produced no sanitizer findings in this harness | supported if PASS |")
    lines.append("| Valgrind reported zero runtime memory errors for the tested flows | supported if PASS |")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- v34 is not a formal memory-safety proof.")
    lines.append("- v34 does not prove constant-time behavior.")
    lines.append("- v34 does not prove thread/TLS safety.")
    lines.append("- v34 does not test Rust FFI.")
    lines.append("- v34 does not test Raspberry Pi or constrained-device behavior.")
    lines.append("- Valgrind coverage is slower and uses fewer iterations than ASan/UBSan.")
    lines.append("")
    lines.append("## Next")
    lines.append("")
    lines.append("v35 should perform constrained-device/Raspberry-Pi-style memory budget validation.")
    lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
