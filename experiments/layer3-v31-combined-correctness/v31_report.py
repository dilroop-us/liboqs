#!/usr/bin/env python3
from pathlib import Path
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

CORRECTNESS = RESULTS / "v31_combined_correctness.csv"
WORKSPACE = RESULTS / "v31_combined_workspace.csv"
BUILD_LOG = RESULTS / "v31_build.log"
RUN_LOG = RESULTS / "v31_combined_correctness_run.log"
SYMS = RESULTS / "v31_lifecycle_symbols.txt"
OUT = RESULTS / "v31_combined_correctness_report.md"


def load_csv(path):
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


correctness = load_csv(CORRECTNESS)
workspace = load_csv(WORKSPACE)

total_iterations = 0
total_passed = 0
total_failed = 0

for row in correctness:
    total_iterations += int(row["iterations"])
    total_passed += int(row["passed"])
    total_failed += int(row["failed"])

overall_status = "PASS" if total_failed == 0 and correctness else "FAIL"

md = "# Layer 3 v31: Combined Correctness Harness\n\n"

md += "## Scope\n\n"
md += "v31 validates the final optimized combined PQC build using:\n\n"
md += "- ML-KEM-768 with v29 lifecycle workspace\n"
md += "- ML-DSA-44 with v24b lifecycle workspace\n"
md += "- one combined C harness linked against the optimized liboqs build\n\n"
md += "v31 is a correctness-validation step. It does not introduce new stack or workspace optimizations.\n\n"

md += "## Workspace setup\n\n"
md += "| Scheme | Workspace kind | Bytes | KiB |\n"
md += "|---|---|---:|---:|\n"

for row in workspace:
    b = int(row["bytes"])
    md += f"| {row['scheme']} | {row['workspace_kind']} | {b} | {b / 1024.0:.2f} |\n"

md += "\n## Correctness results\n\n"
md += "| Test | Iterations | Passed | Failed | Mean us | Status |\n"
md += "|---|---:|---:|---:|---:|---|\n"

for row in correctness:
    md += (
        f"| {row['test']} | {row['iterations']} | {row['passed']} | "
        f"{row['failed']} | {float(row['mean_us']):.3f} | {row['status']} |\n"
    )

md += "\n## Summary\n\n"
md += "| Metric | Value |\n"
md += "|---|---:|\n"
md += f"| total test groups | {len(correctness)} |\n"
md += f"| total iteration groups | {total_iterations} |\n"
md += f"| total passed | {total_passed} |\n"
md += f"| total failed | {total_failed} |\n"
md += f"| overall status | {overall_status} |\n"

md += "\n## What v31 checks\n\n"
md += "| Area | Check |\n"
md += "|---|---|\n"
md += "| ML-KEM | keypair, encapsulation, decapsulation, shared-secret equality |\n"
md += "| ML-DSA | keypair, signing, valid signature verification |\n"
md += "| ML-DSA negative check | modified message rejection |\n"
md += "| ML-DSA negative check | modified signature rejection |\n"
md += "| Combined sequence | ML-KEM key exchange followed by ML-DSA transcript signing and verification |\n"

md += "\n## Claims supported by v31\n\n"
md += "| Claim | Status |\n"
md += "|---|---|\n"
md += "| ML-KEM v29 lifecycle workspace can run valid KEM flow | supported if PASS |\n"
md += "| ML-DSA v24b lifecycle workspace can run valid sign/verify flow | supported if PASS |\n"
md += "| ML-DSA rejects modified messages/signatures in this harness | supported if PASS |\n"
md += "| ML-KEM + ML-DSA can coexist in the same optimized binary | supported if PASS |\n"
md += "| Full misuse, sanitizer, threading, and differential safety | not claimed in v31 |\n"

md += "\n## Limitations\n\n"
md += "- v31 is not a formal proof.\n"
md += "- v31 does not prove constant-time behavior.\n"
md += "- v31 does not test workspace misuse cases deeply; that belongs to v32.\n"
md += "- v31 does not perform baseline-vs-optimized differential testing; that belongs to v33.\n"
md += "- v31 does not run ASan/UBSan/Valgrind; that belongs to v34.\n"
md += "- v31 does not test Rust FFI or Pi behavior.\n\n"

md += "## Next\n\n"
md += "v32 should test workspace API misuse for both ML-KEM and ML-DSA.\n"

OUT.write_text(md)

print(f"wrote {OUT}")
