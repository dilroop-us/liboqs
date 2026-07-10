#!/usr/bin/env python3

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
RESULTS = ROOT / "layer3-results"

CSV_IN = RESULTS / "v38_timing_leakage.csv"
RUN_LOG = RESULTS / "v38_timing_leakage_run.log"
REPORT_OUT = RESULTS / "v38_timing_leakage_report.md"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def extract_config(name: str) -> str:
    if not RUN_LOG.exists():
        return "not found"

    prefix = f"V38_CONFIG,{name},"
    for line in RUN_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line.split(",", 2)[2]
    return "not found"


def extract_workspace(name: str) -> int:
    if not RUN_LOG.exists():
        return 0

    prefix = f"V38_WORKSPACE,{name},"
    for line in RUN_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return int(line.split(",")[2])
    return 0


def main() -> None:
    rows = read_csv(CSV_IN)

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    flagged = sum(1 for r in rows if r["status"] == "FLAG")
    failed = sum(1 for r in rows if r["status"] == "FAIL")

    execution_status = "PASS" if total > 0 and failed == 0 else "FAIL"
    timing_status = "NO_FLAGS" if flagged == 0 and failed == 0 and total > 0 else "FLAGS_OR_FAILURES_PRESENT"

    samples = extract_config("SAMPLES")
    warmup = extract_config("WARMUP")
    threshold = extract_config("THRESHOLD")
    batch = extract_config("BATCH")

    mlkem = extract_workspace("ML-KEM")
    mldsa = extract_workspace("ML-DSA")
    combined = extract_workspace("COMBINED")

    lines: list[str] = []

    lines.append("# Layer 3 v38: Timing / Constant-Time-Style Leakage Validation")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("v38 performs dudect-style timing-distribution screening for selected optimized ML-KEM-768 and ML-DSA-44 lifecycle-workspace operations.")
    lines.append("")
    lines.append("This is statistical timing screening, not a formal constant-time proof.")
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
    lines.append(f"| samples per case | {samples} |")
    lines.append(f"| warmup operations per case | {warmup} |")
    lines.append(f"| Welch t-threshold | {threshold} |")
    lines.append(f"| batch size | {batch} |")
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
    lines.append(f"| total timing rows | {total} |")
    lines.append(f"| PASS rows | {passed} |")
    lines.append(f"| FLAG rows | {flagged} |")
    lines.append(f"| FAIL rows | {failed} |")
    lines.append(f"| execution status | {execution_status} |")
    lines.append(f"| timing classification | {timing_status} |")
    lines.append("")
    lines.append("## Timing results")
    lines.append("")
    lines.append("| Case | Samples | Class 0 n | Class 1 n | Class 0 mean ns | Class 1 mean ns | abs(Welch t) | Threshold | Exec failures | Status | Notes |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")

    for r in rows:
        lines.append(
            f"| {r['case']} | {r['samples']} | {r['class0_n']} | {r['class1_n']} | "
            f"{r['class0_mean_ns']} | {r['class1_mean_ns']} | {r['welch_t_abs']} | "
            f"{r['threshold']} | {r['exec_failures']} | {r['status']} | {r['notes']} |"
        )

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- `PASS` means the tested timing classes stayed below the configured Welch t-threshold.")
    lines.append("- `FLAG` means the tested timing classes exceeded the configured threshold and should be treated as a timing-leakage candidate or public-input timing difference requiring investigation.")
    lines.append("- `FAIL` means the underlying cryptographic operation failed an expected correctness condition during timing collection.")
    lines.append("")
    lines.append("## What v38 checks")
    lines.append("")
    lines.append("| Area | Check |")
    lines.append("|---|---|")
    lines.append("| ML-KEM decapsulation | valid ciphertext timing class vs modified ciphertext timing class |")
    lines.append("| ML-DSA verification | valid signature timing class vs modified signature timing class |")
    lines.append("| ML-DSA signing | fixed message timing class vs alternate message timing class |")
    lines.append("| Combined transcript verification | valid transcript timing class vs modified transcript timing class |")
    lines.append("| Statistical test | absolute Welch t-statistic against configured threshold |")
    lines.append("")
    lines.append("## Claims supported by v38")
    lines.append("")
    lines.append("| Claim | Status |")
    lines.append("|---|---|")
    lines.append("| v38 timing harness executed selected ML-KEM/ML-DSA timing classes without correctness failures | supported if execution status is PASS |")
    lines.append("| no tested timing row exceeded the configured t-threshold | supported only if FLAG rows = 0 |")
    lines.append("| selected timing rows require investigation | supported if FLAG rows > 0 |")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- v38 is not a formal constant-time proof.")
    lines.append("- v38 does not test power, EM, cache, branch predictor, or microarchitectural leakage directly.")
    lines.append("- v38 results can be affected by CPU frequency scaling, OS scheduling, thermal throttling, and background processes.")
    lines.append("- ML-DSA verification timing differences may involve public inputs and are not automatically secret leakage.")
    lines.append("- v38 does not prove production side-channel resistance.")
    lines.append("")
    lines.append("## Next")
    lines.append("")
    lines.append("v39 should produce a final memory/accounting/evidence report tying v31-v38 together, or run a deeper timing follow-up if v38 produces timing flags.")
    lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
