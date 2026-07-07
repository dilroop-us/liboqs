#!/usr/bin/env python3

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
EXP_DIR = ROOT / "experiments" / "layer3-v35-constrained-budget"
RESULTS = ROOT / "layer3-results"

BUILD = ROOT / "build-v35-constrained-budget"
LIB = BUILD / "lib" / "liboqs.a"

SRC = EXP_DIR / "v35_constrained_budget_harness.c"
HEADER = EXP_DIR / "v35_workspace_setup.generated.h"
BIN = RESULTS / "v35_constrained_budget_harness"

BUILD_LOG = RESULTS / "v35_build.log"
RUN_LOG = RESULTS / "v35_constrained_budget_run.log"
TIME_LOG = RESULTS / "v35_time.log"
SYMBOL_LOG = RESULTS / "v35_lifecycle_symbols.txt"
CSV_OUT = RESULTS / "v35_constrained_budget.csv"
SIZE_CSV = RESULTS / "v35_size.csv"
STACK_CSV = RESULTS / "v35_stack_usage.csv"

EXPERIMENTAL_DEFINES = " ".join([
    "-DMLK_CONFIG_EXPERIMENTAL_CALLER_ENC_WORKSPACE",
    "-DMLK_CONFIG_EXPERIMENTAL_CALLER_KEYPAIR_WORKSPACE",
    "-DMLK_CONFIG_EXPERIMENTAL_CALLER_DEC_WORKSPACE",
    "-DMLK_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE",
    "-DMLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE",
    "-DMLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE",
    "-DMLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE",
    "-DMLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE",
    "-DMLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE",
    "-DMLD_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE",
])


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def run_cmd(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    with BUILD_LOG.open("a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(cmd) + "\n")
        f.write(proc.stdout)

    if proc.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(cmd)}")

    return proc


def build_constrained() -> None:
    force = os.environ.get("V35_FORCE_REBUILD", "0") == "1"

    if force and BUILD.exists():
        shutil.rmtree(BUILD)

    if LIB.exists():
        print(f"v35 constrained build already exists: {LIB}")
        return

    c_flags = (
        "-Os -g0 -fno-omit-frame-pointer "
        "-fstack-usage -ffunction-sections -fdata-sections "
        f"{EXPERIMENTAL_DEFINES}"
    )

    run_cmd([
        "cmake",
        "-S", str(ROOT),
        "-B", str(BUILD),
        "-DBUILD_SHARED_LIBS=OFF",
        "-DOQS_MINIMAL_BUILD=KEM_ml_kem_768;SIG_ml_dsa_44",
        "-DOQS_USE_OPENSSL=OFF",
        "-DCMAKE_BUILD_TYPE=MinSizeRel",
        f"-DCMAKE_C_FLAGS={c_flags}",
        "-DCMAKE_EXE_LINKER_FLAGS=-Wl,--gc-sections",
    ], cwd=ROOT)

    run_cmd([
        "cmake",
        "--build", str(BUILD),
        f"-j{os.cpu_count() or 2}",
    ], cwd=ROOT)


def nm_symbols(lib: Path) -> list[str]:
    proc = run_cmd([
        "nm",
        "-g",
        "--defined-only",
        str(lib),
    ], cwd=ROOT)

    SYMBOL_LOG.write_text(proc.stdout, encoding="utf-8")

    symbols: list[str] = []
    for line in proc.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            symbols.append(parts[-1])
    return symbols


def norm(s: str) -> str:
    return s.lower().replace("-", "_")


def generate_workspace_header() -> None:
    symbols = nm_symbols(LIB)
    symset = set(symbols)

    def order_symbol(sym: str) -> tuple[int, str]:
        if "_C_" in sym:
            return (0, sym)
        if "_X86_64_" in sym:
            return (1, sym)
        return (2, sym)

    def is_mlkem_lifecycle(sym: str) -> bool:
        s = norm(sym)
        return (
            ("mlkem" in s or "ml_kem" in s)
            and "768" in s
            and "v29_lifecycle" in s
        )

    def is_mldsa_lifecycle(sym: str) -> bool:
        s = norm(sym)
        return (
            ("mldsa" in s or "ml_dsa" in s)
            and "44" in s
            and "v24_lifecycle" in s
        )

    def collect_pairs(kind: str) -> list[tuple[str, str]]:
        pred = is_mlkem_lifecycle if kind == "mlkem" else is_mldsa_lifecycle

        byte_syms = []
        for sym in symbols:
            if sym.startswith("__odr_asan."):
                continue
            if pred(sym) and sym.endswith("_bytes"):
                byte_syms.append(sym)

        byte_syms = sorted(set(byte_syms), key=order_symbol)

        pairs: list[tuple[str, str]] = []
        for b in byte_syms:
            setter = b[:-len("_bytes")] + "_set"
            if setter in symset:
                pairs.append((b, setter))

        if not pairs:
            raise SystemExit(f"could not find {kind} lifecycle workspace byte/setter pair in {SYMBOL_LOG}")

        return pairs

    mlkem_pairs = collect_pairs("mlkem")
    mldsa_pairs = collect_pairs("mldsa")

    decls: list[str] = []
    for b, setter in mlkem_pairs + mldsa_pairs:
        decls.append(f"extern size_t {b}(void);")
        decls.append(f"extern int {setter}(void *, size_t);")

    def make_need_func(name: str, pairs: list[tuple[str, str]]) -> str:
        lines = [f"static inline size_t v35_{name}_workspace_need(void) {{", "    size_t n = 0;"]
        for b, _ in pairs:
            lines.append(f"    n = v35_max_size_t(n, {b}());")
        lines.append("    return n;")
        lines.append("}")
        return "\n".join(lines)

    def make_set_func(name: str, pairs: list[tuple[str, str]]) -> str:
        lines = [
            f"static inline int v35_{name}_workspace_set(void *ptr) {{",
            f"    const size_t n = v35_{name}_workspace_need();",
            "    int rc = 0;",
        ]
        for _, setter in pairs:
            lines.append(f"    rc |= {setter}(ptr, n);")
        lines.append("    return rc;")
        lines.append("}")
        return "\n".join(lines)

    header = "\n".join([
        "#pragma once",
        "",
        "#include <stddef.h>",
        "#include <stdint.h>",
        "",
        *decls,
        "",
        "static inline size_t v35_max_size_t(size_t a, size_t b) {",
        "    return a > b ? a : b;",
        "}",
        "",
        make_need_func("mlkem", mlkem_pairs),
        "",
        make_need_func("mldsa", mldsa_pairs),
        "",
        make_set_func("mlkem", mlkem_pairs),
        "",
        make_set_func("mldsa", mldsa_pairs),
        "",
    ])

    HEADER.write_text(header, encoding="utf-8")

    print("Workspace symbols:")
    print("  ML-KEM lifecycle pairs:")
    for b, s in mlkem_pairs:
        print(f"    bytes:  {b}")
        print(f"    setter: {s}")
    print("  ML-DSA lifecycle pairs:")
    for b, s in mldsa_pairs:
        print(f"    bytes:  {b}")
        print(f"    setter: {s}")


def compile_harness() -> None:
    includes = [
        "-I", str(BUILD / "include"),
        "-I", str(ROOT / "include"),
        "-I", str(EXP_DIR),
    ]

    run_cmd([
        "cc",
        "-std=c11",
        "-Os",
        "-g0",
        "-fno-omit-frame-pointer",
        "-fstack-usage",
        "-ffunction-sections",
        "-fdata-sections",
        "-Wall",
        "-Wextra",
        *includes,
        str(SRC),
        "-o", str(BIN),
        "-Wl,--gc-sections",
        "-Wl,--start-group",
        str(LIB),
        "-Wl,--end-group",
        "-pthread",
        "-lm",
        "-ldl",
    ], cwd=ROOT)


def run_harness(iterations: int) -> subprocess.CompletedProcess[str]:
    cmd = [
        "/usr/bin/time",
        "-v",
        str(BIN),
        str(iterations),
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    RUN_LOG.write_text(proc.stdout, encoding="utf-8")
    TIME_LOG.write_text(proc.stderr, encoding="utf-8")

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(f"v35 harness failed with exit code {proc.returncode}")

    return proc


def parse_harness_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for line in output.splitlines():
        if line.startswith("V35_BUDGET_RESULT,"):
            _, name, value, budget, status = line.split(",")
            rows.append({
                "category": "workspace",
                "name": name,
                "value": value,
                "budget": budget,
                "iterations": "",
                "passed": "",
                "failed": "",
                "status": status,
                "notes": "explicit workspace budget",
            })

        elif line.startswith("V35_CASE,"):
            _, name, iterations, passed, failed, status = line.split(",")
            rows.append({
                "category": "correctness",
                "name": name,
                "value": "",
                "budget": "",
                "iterations": iterations,
                "passed": passed,
                "failed": failed,
                "status": status,
                "notes": "optimized flow correctness",
            })

    return rows


def parse_size_binary(path: Path) -> dict[str, int]:
    proc = subprocess.run(
        ["size", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if proc.returncode != 0:
        return {"text": 0, "data": 0, "bss": 0, "dec": 0}

    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return {"text": 0, "data": 0, "bss": 0, "dec": 0}

    parts = lines[1].split()
    if len(parts) < 4:
        return {"text": 0, "data": 0, "bss": 0, "dec": 0}

    return {
        "text": int(parts[0]),
        "data": int(parts[1]),
        "bss": int(parts[2]),
        "dec": int(parts[3]),
    }


def parse_max_rss_kb() -> int:
    text = TIME_LOG.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Maximum resident set size \(kbytes\):\s+(\d+)", text)
    return int(m.group(1)) if m else 0


def collect_size_rows() -> list[dict[str, str]]:
    lib_budget = env_int("V35_LIB_BUDGET_BYTES", 8 * 1024 * 1024)
    bin_budget = env_int("V35_BIN_BUDGET_BYTES", 16 * 1024 * 1024)
    rss_budget = env_int("V35_RSS_BUDGET_KB", 128 * 1024)

    lib_size = LIB.stat().st_size if LIB.exists() else 0
    bin_size = BIN.stat().st_size if BIN.exists() else 0
    bin_sections = parse_size_binary(BIN)
    rss_kb = parse_max_rss_kb()

    rows = [
        {
            "metric": "liboqs_archive_bytes",
            "value": str(lib_size),
            "budget": str(lib_budget),
            "status": "PASS" if lib_size <= lib_budget else "FAIL",
        },
        {
            "metric": "harness_binary_bytes",
            "value": str(bin_size),
            "budget": str(bin_budget),
            "status": "PASS" if bin_size <= bin_budget else "FAIL",
        },
        {
            "metric": "harness_text_bytes",
            "value": str(bin_sections["text"]),
            "budget": "",
            "status": "INFO",
        },
        {
            "metric": "harness_data_bytes",
            "value": str(bin_sections["data"]),
            "budget": "",
            "status": "INFO",
        },
        {
            "metric": "harness_bss_bytes",
            "value": str(bin_sections["bss"]),
            "budget": "",
            "status": "INFO",
        },
        {
            "metric": "harness_dec_bytes",
            "value": str(bin_sections["dec"]),
            "budget": "",
            "status": "INFO",
        },
        {
            "metric": "max_rss_kb",
            "value": str(rss_kb),
            "budget": str(rss_budget),
            "status": "PASS" if rss_kb <= rss_budget else "FAIL",
        },
    ]

    with SIZE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value", "budget", "status"])
        writer.writeheader()
        writer.writerows(rows)

    return rows


def parse_stack_usage_files() -> tuple[list[dict[str, str]], int]:
    candidates: set[Path] = set()

    # Only collect stack-usage files from the v35 build/harness.
    # Do not scan the whole repository, because older layer builds also contain .su files.
    if BUILD.exists():
        candidates.update(BUILD.rglob("*.su"))

    if EXP_DIR.exists():
        candidates.update(EXP_DIR.glob("*.su"))

    if RESULTS.exists():
        candidates.update(RESULTS.glob("v35*.su"))

    candidates.update(ROOT.glob("v35*.su"))

    stack_rows: list[dict[str, str]] = []

    for path in sorted(candidates):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) >= 3:
                func = parts[0]
                bytes_s = parts[1]
                kind = parts[2]
            else:
                bits = line.split()
                if len(bits) < 3:
                    continue
                func = bits[0]
                bytes_s = bits[-2]
                kind = bits[-1]

            try:
                stack_bytes = int(bytes_s)
            except ValueError:
                continue

            stack_rows.append({
                "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                "function": func,
                "bytes": str(stack_bytes),
                "kind": kind,
            })

    # Exclude liboqs test-suite stack entries from the final budget scan.
    # v35 is meant to report the optimized library/harness constrained-device footprint.
    stack_rows = [
        r for r in stack_rows
        if "/tests/" not in r["file"] and not r["file"].startswith("build-v35-constrained-budget/tests/")
    ]

    stack_rows.sort(key=lambda r: int(r["bytes"]), reverse=True)

    max_stack = int(stack_rows[0]["bytes"]) if stack_rows else 0

    with STACK_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "function", "bytes", "kind"])
        writer.writeheader()
        writer.writerows(stack_rows[:100])

    return stack_rows, max_stack


def write_main_csv(rows: list[dict[str, str]]) -> None:
    fields = ["category", "name", "value", "budget", "iterations", "passed", "failed", "status", "notes"]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    BUILD_LOG.write_text("", encoding="utf-8")

    iterations = env_int("V35_ITERATIONS", 100)
    stack_budget = env_int("V35_STACK_BUDGET_BYTES", 64 * 1024)

    build_constrained()
    generate_workspace_header()
    compile_harness()

    proc = run_harness(iterations)

    rows = parse_harness_rows(proc.stdout)

    size_rows = collect_size_rows()
    for r in size_rows:
        if r["status"] == "INFO":
            continue
        rows.append({
            "category": "resource",
            "name": r["metric"],
            "value": r["value"],
            "budget": r["budget"],
            "iterations": "",
            "passed": "",
            "failed": "",
            "status": r["status"],
            "notes": "size/rss budget",
        })

    _, max_stack = parse_stack_usage_files()
    rows.append({
        "category": "resource",
        "name": "max_static_stack_usage_bytes",
        "value": str(max_stack),
        "budget": str(stack_budget),
        "iterations": "",
        "passed": "",
        "failed": "",
        "status": "PASS" if max_stack <= stack_budget else "FAIL",
        "notes": "max .su static stack usage",
    })

    write_main_csv(rows)

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = sum(1 for r in rows if r["status"] == "FAIL")

    print(f"v35 summary: total_rows={total} pass_rows={passed} fail_rows={failed}")

    if failed != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
