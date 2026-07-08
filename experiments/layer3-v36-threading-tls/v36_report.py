#!/usr/bin/env python3

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
RESULTS = ROOT / "layer3-results"

CSV_IN = RESULTS / "v36_threading_tls.csv"
RUN_LOG = RESULTS / "v36_threading_tls_run.log"
REPORT_OUT = RESULTS / "v36_threading_tls_report.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def extract_value(prefix: str) -> str:
    if not RUN_LOG.exists():
        return "not found"

    text = RUN_LOG.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(",", 2)[2]
    return "not found"


def extract_workspace(name: str) -> int:
    if not RUN_LOG.exists():
        return 0

    text = RUN_LOG.read_text(encoding="utf-8", errors="replace")
    prefix = f"V36_WORKSPACE,{name},"

    for line in text.splitlines():
        if line.startswith(prefix):
            return int(line.split(",")[2])

    return 0


def main() -> None:
    rows = read_csv(CSV_IN)

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = sum(1 for r in rows if r["status"] == "FAIL")
    overall = "PASS" if failed == 0 and total > 0 else "FAIL"

    threads = extract_value("V36_CONFIG,THREADS,")
    iterations = extract_value("V36_CONFIG,ITERATIONS_PER_THREAD,")

    mlkem = extract_workspace("ML-KEM")
    mldsa = extract_workspace("ML-DSA")
    combined = extract_workspace("COMBINED")

    lines: list[str] = []

    lines.append("# Layer 3 v36: Threading/TLS Workspace Validation")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("v36 validates whether the optimized lifecycle-workspace implementation works under concurrent thread execution.")
    lines.append("")
    lines.append("Each worker thread allocates its own caller-owned ML-KEM and/or ML-DSA workspace, sets the lifecycle workspace pointer inside that thread, and then runs optimized cryptographic flows concurrently.")
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
    lines.append(f"| threads | {threads} |")
    lines.append(f"| iterations per thread | {iterations} |")
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
    lines.append(f"| overall v36 status | {overall} |")
    lines.append("")
    lines.append("## Threading/TLS results")
    lines.append("")
    lines.append("| Case | Threads | Iterations/thread | Total ops | Passed ops | Worker failures | Canary failures | Status | Notes |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|---|")

    for r in rows:
        lines.append(
            f"| {r['case']} | {r['threads']} | {r['iterations_per_thread']} | {r['total_ops']} | {r['passed_ops']} | {r['worker_failures']} | {r['canary_failures']} | {r['status']} | {r['notes']} |"
        )

    lines.append("")
    lines.append("## What v36 checks")
    lines.append("")
    lines.append("| Area | Check |")
    lines.append("|---|---|")
    lines.append("| Thread-local workspace setup | each thread sets its own ML-KEM and/or ML-DSA lifecycle workspace |")
    lines.append("| ML-KEM concurrency | concurrent keypair, encaps, decaps, shared-secret equality |")
    lines.append("| ML-DSA concurrency | concurrent keypair, sign, verify, reject modified message/signature |")
    lines.append("| Combined concurrency | concurrent KEM transcript construction and ML-DSA signature verification |")
    lines.append("| Repeated setter stress | each worker repeatedly re-sets workspace pointers before operations |")
    lines.append("| Canary integrity | guard regions before and after each workspace are checked for corruption |")
    lines.append("")
    lines.append("## Claims supported by v36")
    lines.append("")
    lines.append("| Claim | Status |")
    lines.append("|---|---|")
    lines.append("| optimized lifecycle-workspace flows work under concurrent execution when each thread sets its own workspace | supported if PASS |")
    lines.append("| ML-KEM and ML-DSA workspaces showed no guard/canary corruption in this harness | supported if PASS |")
    lines.append("| repeated workspace setter calls did not break correctness in this threaded harness | supported if PASS |")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- v36 is not a formal proof of thread safety.")
    lines.append("- v36 does not prove all possible scheduler interleavings.")
    lines.append("- v36 does not use ThreadSanitizer.")
    lines.append("- v36 does not prove Rust async safety.")
    lines.append("- v36 does not prove constant-time behavior.")
    lines.append("- v36 does not prove production readiness.")
    lines.append("")
    lines.append("## Next")
    lines.append("")
    lines.append("v37 should perform build matrix validation across selected compiler/build configurations.")
    lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
