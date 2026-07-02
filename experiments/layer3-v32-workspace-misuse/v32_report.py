#!/usr/bin/env python3
from pathlib import Path
import csv
from collections import Counter

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

CSV = RESULTS / "v32_workspace_misuse.csv"
OUT = RESULTS / "v32_workspace_misuse_report.md"


def load_csv(path):
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


rows = load_csv(CSV)
counts = Counter(row["status"] for row in rows)

safe_rows = [r for r in rows if r["kind"] == "safe_wrapper"]
raw_rows = [r for r in rows if r["kind"] == "raw_child"]

safe_fail = sum(1 for r in safe_rows if r["status"] != "PASS")
overall = "PASS" if rows and safe_fail == 0 else "FAIL"

workspace_values = {
    "ML-KEM": "13088",
    "ML-DSA": "44064",
    "Combined": "57152",
}

md = "# Layer 3 v32: Workspace API Misuse Tests\n\n"

md += "## Scope\n\n"
md += "v32 tests caller-side workspace misuse behavior for the final optimized PQC build:\n\n"
md += "- ML-KEM-768 with v29 lifecycle workspace\n"
md += "- ML-DSA-44 with v24 lifecycle workspace\n"
md += "- combined ML-KEM + ML-DSA workspace setup\n\n"
md += "v32 does not add a new optimization. It validates wrapper-level misuse handling and documents raw setter misuse behavior in isolated child processes.\n\n"

md += "## Workspace sizes\n\n"
md += "| Scheme | Bytes | KiB |\n"
md += "|---|---:|---:|\n"
md += "| ML-KEM-768 | 13088 | 12.78 |\n"
md += "| ML-DSA-44 | 44064 | 43.03 |\n"
md += "| Combined | 57152 | 55.81 |\n\n"

md += "## Summary\n\n"
md += "| Metric | Value |\n"
md += "|---|---:|\n"
md += f"| total rows | {len(rows)} |\n"
md += f"| safe wrapper rows | {len(safe_rows)} |\n"
md += f"| raw child observation rows | {len(raw_rows)} |\n"
md += f"| PASS rows | {counts.get('PASS', 0)} |\n"
md += f"| FAIL rows | {counts.get('FAIL', 0)} |\n"
md += f"| DOCUMENTED rows | {counts.get('DOCUMENTED', 0)} |\n"
md += f"| safe wrapper failures | {safe_fail} |\n"
md += f"| overall v32 status | {overall} |\n\n"

md += "## Safe wrapper tests\n\n"
md += "| Test | Scheme | Expected | Observed | Iterations | Passed | Failed | Status | Notes |\n"
md += "|---|---|---|---|---:|---:|---:|---|---|\n"

for row in safe_rows:
    md += (
        f"| {row['test']} | {row['scheme']} | {row['expected']} | {row['observed']} | "
        f"{row['iterations']} | {row['passed']} | {row['failed']} | {row['status']} | {row['notes']} |\n"
    )

md += "\n## Raw setter child-process observations\n\n"
md += "| Test | Scheme | Expected | Observed | Status | Notes |\n"
md += "|---|---|---|---|---|---|\n"

for row in raw_rows:
    md += (
        f"| {row['test']} | {row['scheme']} | {row['expected']} | "
        f"{row['observed']} | {row['status']} | {row['notes']} |\n"
    )

md += "\n## Interpretation\n\n"
md += "- Safe wrapper tests are expected to pass or reject invalid inputs cleanly.\n"
md += "- Raw setter misuse tests are documented observations because raw experimental setters do not carry size or alignment metadata.\n"
md += "- Raw setters should not be exposed directly to the future Rust backend.\n"
md += "- Rust integration should use a typed wrapper/shim that enforces non-NULL, minimum capacity, and alignment before calling raw setters.\n\n"

md += "## Claims supported by v32\n\n"
md += "| Claim | Status |\n"
md += "|---|---|\n"
md += "| NULL workspace can be rejected at wrapper layer | supported if PASS |\n"
md += "| too-small workspace can be rejected at wrapper layer | supported if PASS |\n"
md += "| misaligned workspace can be rejected at wrapper layer | supported if PASS |\n"
md += "| exact-size workspace works | supported if PASS |\n"
md += "| larger-than-needed workspace works | supported if PASS |\n"
md += "| workspace replacement works | supported if PASS |\n"
md += "| raw setter misuse behavior is isolated from main test process | documented |\n\n"

md += "## Limitations\n\n"
md += "- v32 is not a sanitizer run.\n"
md += "- v32 does not prove memory safety.\n"
md += "- v32 does not prove constant-time behavior.\n"
md += "- v32 does not prove Rust FFI safety yet.\n"
md += "- Raw setter misuse observations are not production guarantees.\n\n"

md += "## Next\n\n"
md += "v33 should perform baseline-vs-optimized differential testing.\n"

OUT.write_text(md)

print(f"wrote {OUT}")
