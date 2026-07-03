#!/usr/bin/env python3
from pathlib import Path
import csv
from collections import Counter

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

CSV = RESULTS / "v33_differential.csv"
OUT = RESULTS / "v33_differential_report.md"


def load_csv(path):
    if not path.exists():
        return []

    with path.open() as f:
        return list(csv.DictReader(f))


rows = load_csv(CSV)
counts = Counter(row["status"] for row in rows)

fail_rows = [r for r in rows if r["status"] != "PASS"]
overall = "PASS" if rows and not fail_rows else "FAIL"

interop_rows = [
    r for r in rows
    if r["consumer"] in ("baseline", "optimized")
]

md = "# Layer 3 v33: Baseline-vs-Optimized Differential Tests\n\n"

md += "## Scope\n\n"
md += "v33 checks behavioral compatibility between baseline/reference liboqs and the optimized lifecycle-workspace liboqs build.\n\n"
md += "The optimized build uses:\n\n"
md += "- ML-KEM-768 with v29 lifecycle workspace\n"
md += "- ML-DSA-44 with v24 lifecycle workspace\n\n"
md += "v33 does not add new stack or workspace optimizations. It is a differential compatibility validation step.\n\n"

md += "## Workspace sizes for optimized build\n\n"
md += "| Scheme | Bytes | KiB |\n"
md += "|---|---:|---:|\n"
md += "| ML-KEM-768 | 13088 | 12.78 |\n"
md += "| ML-DSA-44 | 44064 | 43.03 |\n"
md += "| Combined | 57152 | 55.81 |\n\n"

md += "## Summary\n\n"
md += "| Metric | Value |\n"
md += "|---|---:|\n"
md += f"| total rows | {len(rows)} |\n"
md += f"| interoperability rows | {len(interop_rows)} |\n"
md += f"| PASS rows | {counts.get('PASS', 0)} |\n"
md += f"| FAIL rows | {counts.get('FAIL', 0)} |\n"
md += f"| overall v33 status | {overall} |\n\n"

md += "## Differential results\n\n"
md += "| Test | Producer | Consumer | Operation | Iterations | Passed | Failed | Status | Notes |\n"
md += "|---|---|---|---|---:|---:|---:|---|---|\n"

for row in rows:
    md += (
        f"| {row['test']} | {row['producer']} | {row['consumer']} | "
        f"{row['operation']} | {row['iterations']} | {row['passed']} | "
        f"{row['failed']} | {row['status']} | {row['notes']} |\n"
    )

md += "\n## What v33 checks\n\n"
md += "| Area | Check |\n"
md += "|---|---|\n"
md += "| ML-KEM | baseline generated keys/ciphertexts/shared secrets are consumed by optimized build |\n"
md += "| ML-KEM | optimized generated keys/ciphertexts/shared secrets are consumed by baseline build |\n"
md += "| ML-DSA | baseline generated signatures verify in optimized build |\n"
md += "| ML-DSA | optimized generated signatures verify in baseline build |\n"
md += "| ML-DSA negative checks | modified messages and signatures are rejected during consume tests |\n"
md += "| Combined | baseline KEM transcript plus DSA signature is consumed by optimized build |\n"
md += "| Combined | optimized KEM transcript plus DSA signature is consumed by baseline build |\n\n"

md += "## Claims supported by v33\n\n"
md += "| Claim | Status |\n"
md += "|---|---|\n"
md += "| optimized ML-KEM remains interoperable with baseline ML-KEM | supported if PASS |\n"
md += "| optimized ML-DSA remains interoperable with baseline ML-DSA | supported if PASS |\n"
md += "| optimized combined KEM transcript plus DSA signature flow remains baseline-compatible | supported if PASS |\n"
md += "| lifecycle-workspace changes did not break baseline-level API behavior in this harness | supported if PASS |\n\n"

md += "## Limitations\n\n"
md += "- v33 is not a formal proof.\n"
md += "- v33 does not prove constant-time behavior.\n"
md += "- v33 does not run sanitizers.\n"
md += "- v33 does not prove memory safety.\n"
md += "- v33 does not prove threading/TLS safety.\n"
md += "- v33 does not test Rust FFI.\n"
md += "- v33 does not test Pi/constrained-device behavior.\n\n"

md += "## Next\n\n"
md += "v34 should run ASan/UBSan/Valgrind-style memory-safety validation.\n"

OUT.write_text(md)
print(f"wrote {OUT}")
