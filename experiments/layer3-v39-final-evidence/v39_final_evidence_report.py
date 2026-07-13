#!/usr/bin/env python3

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
RESULTS = ROOT / "layer3-results"

CSV_OUT = RESULTS / "v39_evidence_summary.csv"
REPORT_OUT = RESULTS / "v39_final_evidence_report.md"


@dataclass
class Layer:
    layer: str
    title: str
    purpose: str
    expected_report_names: list[str]
    supported_claim: str
    limitation: str


LAYERS: list[Layer] = [
    Layer(
        "v31",
        "Optimized correctness",
        "Validate optimized ML-KEM/ML-DSA lifecycle-workspace correctness.",
        [
            "v31_combined_correctness_report.md",
            "v31_optimized_correctness_report.md",
            "v31_report.md",
        ],
        "Optimized ML-KEM-768, ML-DSA-44, and combined flow correctness passed in the tested harness.",
        "Empirical correctness testing only; not a formal proof.",
    ),
    Layer(
        "v32",
        "Workspace misuse / guard validation",
        "Validate caller-owned workspace guard behavior and misuse handling.",
        [
            "v32_workspace_misuse_report.md",
            "v32_workspace_guard_report.md",
            "v32_report.md",
        ],
        "Workspace guard/misuse checks passed for tested misuse scenarios.",
        "Does not prove every misuse pattern or memory-safety property.",
    ),
    Layer(
        "v33",
        "Baseline-vs-optimized differential compatibility",
        "Validate optimized build against baseline/reference liboqs behavior.",
        [
            "v33_differential_report.md",
            "v33_differential_compatibility_report.md",
            "v33_report.md",
        ],
        "Baseline and optimized builds were interoperable for tested ML-KEM, ML-DSA, and combined flows.",
        "Does not prove equivalence for all possible inputs or configurations.",
    ),
    Layer(
        "v34",
        "Memory-safety validation",
        "Run sanitizer and Valgrind-style memory-safety validation.",
        [
            "v34_memory_safety_report.md",
            "v34_report.md",
        ],
        "ASan/UBSan and Valgrind found no issues in the tested optimized flows.",
        "Does not prove formal memory safety.",
    ),
    Layer(
        "v35",
        "Constrained-device / memory-budget validation",
        "Validate workspace and host-side constrained memory budget.",
        [
            "v35_constrained_budget_report.md",
            "v35_budget_report.md",
            "v35_report.md",
        ],
        "Optimized build fit within the selected 64 KiB combined explicit workspace budget while preserving correctness.",
        "Host-side constrained-device-style evidence; not a real hardware deployment proof.",
    ),
    Layer(
        "v36",
        "Threading / TLS workspace validation",
        "Validate concurrent execution with independent caller-owned workspaces.",
        [
            "v36_threading_tls_report.md",
            "v36_threading_report.md",
            "v36_report.md",
        ],
        "Concurrent ML-KEM, ML-DSA, and combined flows passed with independent thread workspaces.",
        "Does not prove all scheduler interleavings or Rust async/threading safety.",
    ),
    Layer(
        "v37",
        "Build matrix validation",
        "Validate selected Release, RelWithDebInfo, Debug, and size-focused builds.",
        [
            "v37_build_matrix_report.md",
            "v37_report.md",
        ],
        "Selected build configurations exposed required lifecycle symbols and passed core correctness checks.",
        "Does not test every compiler, architecture, OS, or CMake option.",
    ),
    Layer(
        "v38",
        "Timing / constant-time-style leakage validation",
        "Run dudect-style timing-distribution screening.",
        [
            "v38_timing_leakage_report.md",
            "v38_report.md",
        ],
        "Selected timing classes produced no timing flags under the configured Welch t-threshold.",
        "Statistical timing evidence only; not a formal constant-time or side-channel proof.",
    ),
]


def run_git(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return proc.stdout.strip()
    except Exception as exc:
        return f"git command failed: {exc}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def find_report(layer: Layer) -> Path | None:
    for name in layer.expected_report_names:
        p = RESULTS / name
        if p.exists():
            return p

    matches = sorted(RESULTS.glob(f"{layer.layer}*report*.md"))
    if matches:
        return matches[0]

    matches = sorted(RESULTS.glob(f"{layer.layer}*.md"))
    if matches:
        return matches[0]

    return None


def extract_status(text: str, layer: str) -> str:
    lowered = text.lower()

    # v38 has a stronger timing-specific status.
    if layer == "v38":
        if "execution status | pass" in lowered and "timing classification | no_flags" in lowered:
            return "PASS_NO_FLAGS"
        if re.search(r"\|\s*flag rows\s*\|\s*0\s*\|", lowered) and re.search(r"\|\s*fail rows\s*\|\s*0\s*\|", lowered):
            return "PASS_NO_FLAGS"
        if re.search(r"flag_rows\s*=\s*0", lowered) and re.search(r"fail_rows\s*=\s*0", lowered):
            return "PASS_NO_FLAGS"
        if re.search(r"\|\s*fail rows\s*\|\s*0\s*\|", lowered):
            return "PASS_WITH_FLAGS"

    # Markdown table style:
    # | overall status | PASS |
    # | overall v37 status | PASS |
    if re.search(r"\|\s*overall[^|]*status\s*\|\s*pass\s*\|", lowered):
        return "PASS"

    # Plain text style:
    # overall v37 status | PASS
    # overall status: PASS
    if re.search(r"overall[^\n]*status\s*[:|]\s*pass", lowered):
        return "PASS"

    # Markdown summary style:
    # | total failed | 0 |
    # | total passed | 3000 |
    if re.search(r"\|\s*total failed\s*\|\s*0\s*\|", lowered) and re.search(r"\|\s*total passed\s*\|", lowered):
        return "PASS"

    # Generic rows style.
    if re.search(r"\|\s*fail rows\s*\|\s*0\s*\|", lowered) and re.search(r"\|\s*pass rows\s*\|", lowered):
        return "PASS"

    # Log style.
    if re.search(r"fail_rows\s*=\s*0", lowered) and re.search(r"pass_rows\s*=", lowered):
        return "PASS"

    # Table component style:
    # correctness rows contain PASS and Failed column is 0.
    if layer == "v31":
        if "correctness results" in lowered and "| overall status | pass |" in lowered:
            return "PASS"
        if "correctness results" in lowered and "| total failed | 0 |" in lowered:
            return "PASS"

    if "fail" in lowered:
        return "CHECK_REPORT"

    return "UNKNOWN"

def extract_first_match(text: str, patterns: list[str], default: str = "not found") -> str:
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return default


def extract_workspace_bytes(texts: list[str], label: str) -> str:
    patterns = [
        rf"\|\s*{re.escape(label)}(?:-768|-44)?\s*\|\s*(\d+)\s*\|",
        rf"{re.escape(label)} workspace:\s*(\d+)",
        rf"V\d+_WORKSPACE,{re.escape(label)},(\d+)",
        rf"{re.escape(label)}.*?(\d+)\s*/\s*\d+",
    ]

    for text in texts:
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return m.group(1)

    return "not found"


def build_evidence_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for layer in LAYERS:
        report = find_report(layer)

        if report is None:
            rows.append({
                "layer": layer.layer,
                "title": layer.title,
                "purpose": layer.purpose,
                "report": "not found",
                "report_present": "no",
                "status": "MISSING_REPORT",
                "sha256": "not found",
                "supported_claim": layer.supported_claim,
                "limitation": layer.limitation,
            })
            continue

        text = report.read_text(encoding="utf-8", errors="replace")
        status = extract_status(text, layer.layer)

        rows.append({
            "layer": layer.layer,
            "title": layer.title,
            "purpose": layer.purpose,
            "report": str(report.relative_to(ROOT)),
            "report_present": "yes",
            "status": status,
            "sha256": sha256_file(report),
            "supported_claim": layer.supported_claim,
            "limitation": layer.limitation,
        })

    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "layer",
        "title",
        "purpose",
        "report",
        "report_present",
        "status",
        "sha256",
        "supported_claim",
        "limitation",
    ]

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def report_texts(rows: list[dict[str, str]]) -> list[str]:
    texts: list[str] = []

    for row in rows:
        report = row["report"]
        if report != "not found":
            p = ROOT / report
            if p.exists():
                texts.append(p.read_text(encoding="utf-8", errors="replace"))

    return texts


def write_report(rows: list[dict[str, str]]) -> None:
    texts = report_texts(rows)

    mlkem_ws = extract_workspace_bytes(texts, "ML-KEM")
    mldsa_ws = extract_workspace_bytes(texts, "ML-DSA")

    combined_ws = "not found"
    if mlkem_ws.isdigit() and mldsa_ws.isdigit():
        combined_ws = str(int(mlkem_ws) + int(mldsa_ws))
    else:
        combined_ws = extract_workspace_bytes(texts, "COMBINED")

    total = len(rows)
    pass_like = sum(1 for r in rows if r["status"] in {"PASS", "PASS_NO_FLAGS"})
    with_flags = sum(1 for r in rows if r["status"] == "PASS_WITH_FLAGS")
    missing = sum(1 for r in rows if r["status"] == "MISSING_REPORT")
    unknown = sum(1 for r in rows if r["status"] in {"UNKNOWN", "CHECK_REPORT"})

    all_clean = total > 0 and pass_like == total and missing == 0 and unknown == 0 and with_flags == 0
    final_status = "PASS" if all_clean else "CHECK_REPORTS"

    git_head = run_git(["rev-parse", "--short", "HEAD"])
    git_branch = run_git(["branch", "--show-current"])
    git_log = run_git(["log", "--oneline", "-12"])
    git_status = run_git(["status", "--short"])

    lines: list[str] = []

    lines.append("# Layer 3 v39: Final Evidence / Memory-Accounting Report")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("v39 consolidates the Layer 3 validation evidence for the optimized lifecycle-workspace implementation of:")
    lines.append("")
    lines.append("- ML-KEM-768 with v29 lifecycle workspace")
    lines.append("- ML-DSA-44 with v24 lifecycle workspace")
    lines.append("")
    lines.append("This report ties together v31 through v38 and records the empirical claims supported by the validation chain.")
    lines.append("")
    lines.append("v39 does not run a new cryptographic primitive test. It is an evidence, accounting, and claims-boundary report.")
    lines.append("")
    lines.append("## Repository state")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| branch | `{git_branch or 'unknown'}` |")
    lines.append(f"| HEAD | `{git_head or 'unknown'}` |")
    lines.append(f"| working tree status | `{git_status if git_status else 'clean at report generation'}` |")
    lines.append("")
    lines.append("## Final summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| evidence layers checked | {total} |")
    lines.append(f"| clean PASS layers | {pass_like} |")
    lines.append(f"| PASS with timing flags | {with_flags} |")
    lines.append(f"| missing reports | {missing} |")
    lines.append(f"| unknown/check reports | {unknown} |")
    lines.append(f"| final v39 status | {final_status} |")
    lines.append("")
    lines.append("## Memory accounting")
    lines.append("")
    lines.append("| Item | Bytes | KiB |")
    lines.append("|---|---:|---:|")

    def kib(v: str) -> str:
        return f"{int(v) / 1024:.2f}" if v.isdigit() else "not found"

    lines.append(f"| ML-KEM-768 lifecycle workspace | {mlkem_ws} | {kib(mlkem_ws)} |")
    lines.append(f"| ML-DSA-44 lifecycle workspace | {mldsa_ws} | {kib(mldsa_ws)} |")
    lines.append(f"| Combined explicit workspace | {combined_ws} | {kib(combined_ws)} |")
    lines.append("")
    lines.append("## Evidence chain")
    lines.append("")
    lines.append("| Layer | Title | Status | Evidence report | Supported claim |")
    lines.append("|---|---|---|---|---|")

    for r in rows:
        lines.append(
            f"| {r['layer']} | {r['title']} | {r['status']} | "
            f"`{r['report']}` | {r['supported_claim']} |"
        )

    lines.append("")
    lines.append("## Claims supported by v31-v38")
    lines.append("")
    lines.append("If all evidence rows are PASS/PASS_NO_FLAGS, the Layer 3 validation chain supports the following empirical claim:")
    lines.append("")
    lines.append("> Across v31-v38, the optimized ML-KEM-768 and ML-DSA-44 lifecycle-workspace implementation passed correctness, workspace misuse/guard, baseline differential compatibility, sanitizer/memory-safety, constrained-budget, threading/TLS, selected build-matrix, and selected timing-distribution validation.")
    lines.append("")
    lines.append("More specifically:")
    lines.append("")
    lines.append("- v31 supports optimized correctness for the tested ML-KEM, ML-DSA, and combined flows.")
    lines.append("- v32 supports tested workspace misuse/guard behavior.")
    lines.append("- v33 supports baseline-vs-optimized differential compatibility for tested flows.")
    lines.append("- v34 supports sanitizer and Valgrind memory-safety evidence for tested flows.")
    lines.append("- v35 supports the 64 KiB combined explicit workspace budget claim under host-side constrained-device-style testing.")
    lines.append("- v36 supports concurrent execution with independent caller-owned workspaces.")
    lines.append("- v37 supports selected build-profile portability across Release, RelWithDebInfo, Debug, and size-focused static builds.")
    lines.append("- v38 supports statistical timing-distribution evidence with no timing flags in the selected timing classes.")
    lines.append("")
    lines.append("## Claims not supported")
    lines.append("")
    lines.append("This validation package does not prove:")
    lines.append("")
    lines.append("- formal correctness")
    lines.append("- formal memory safety")
    lines.append("- formal constant-time behavior")
    lines.append("- power, EM, cache, branch-predictor, or microarchitectural side-channel resistance")
    lines.append("- all compiler, OS, CPU, architecture, or CMake configuration portability")
    lines.append("- Rust FFI safety")
    lines.append("- Raspberry Pi hardware readiness unless separately tested on Pi hardware")
    lines.append("- production readiness")
    lines.append("")
    lines.append("## Evidence artifact hashes")
    lines.append("")
    lines.append("| Layer | Report | SHA-256 |")
    lines.append("|---|---|---|")

    for r in rows:
        lines.append(f"| {r['layer']} | `{r['report']}` | `{r['sha256']}` |")

    lines.append("")
    lines.append("## Layer-specific limitations")
    lines.append("")
    lines.append("| Layer | Limitation |")
    lines.append("|---|---|")

    for r in rows:
        lines.append(f"| {r['layer']} | {r['limitation']} |")

    lines.append("")
    lines.append("## Recent git log")
    lines.append("")
    lines.append("```text")
    lines.append(git_log if git_log else "not available")
    lines.append("```")
    lines.append("")
    lines.append("## Recommended next step")
    lines.append("")
    lines.append("After v39, the next useful validation target is Rust FFI / integration validation, because v31-v39 are C/liboqs-side evidence. A later step can also run real Raspberry Pi hardware validation if Pi readiness is a goal.")
    lines.append("")

    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = build_evidence_rows()
    write_csv(rows)
    write_report(rows)

    total = len(rows)
    pass_like = sum(1 for r in rows if r["status"] in {"PASS", "PASS_NO_FLAGS"})
    with_flags = sum(1 for r in rows if r["status"] == "PASS_WITH_FLAGS")
    missing = sum(1 for r in rows if r["status"] == "MISSING_REPORT")
    unknown = sum(1 for r in rows if r["status"] in {"UNKNOWN", "CHECK_REPORT"})

    final_status = "PASS" if pass_like == total and with_flags == 0 and missing == 0 and unknown == 0 else "CHECK_REPORTS"

    print(f"v39 summary: total_layers={total} pass_layers={pass_like} pass_with_flags={with_flags} missing_reports={missing} unknown_reports={unknown}")
    print(f"overall v39 status | {final_status}")
    print(f"wrote {CSV_OUT}")
    print(f"wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
