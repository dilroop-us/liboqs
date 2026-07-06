#!/usr/bin/env python3

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
EXP_DIR = ROOT / "experiments" / "layer3-v34-memory-safety"
RESULTS = ROOT / "layer3-results"

ASAN_BUILD = ROOT / "build-v34-asan-ubsan"
VALGRIND_BUILD = ROOT / "build-v34-valgrind"

ASAN_LIB = ASAN_BUILD / "lib" / "liboqs.a"
VALGRIND_LIB = VALGRIND_BUILD / "lib" / "liboqs.a"

SRC = EXP_DIR / "v34_memory_safety_harness.c"
HEADER = EXP_DIR / "v34_workspace_setup.generated.h"

ASAN_BIN = RESULTS / "v34_asan_ubsan_harness"
VALGRIND_BIN = RESULTS / "v34_valgrind_harness"

BUILD_LOG = RESULTS / "v34_build.log"
ASAN_LOG = RESULTS / "v34_asan_ubsan_run.log"
VALGRIND_LOG = RESULTS / "v34_valgrind_run.log"
SYMBOL_LOG = RESULTS / "v34_lifecycle_symbols.txt"
CSV_OUT = RESULTS / "v34_memory_safety.csv"

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


def run_cmd(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
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


def run_cmd_no_raise(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def build_asan_ubsan() -> None:
    if ASAN_LIB.exists():
        print(f"ASan/UBSan build already exists: {ASAN_LIB}")
        return

    run_cmd([
        "cmake",
        "-S", str(ROOT),
        "-B", str(ASAN_BUILD),
        "-DBUILD_SHARED_LIBS=OFF",
        "-DOQS_MINIMAL_BUILD=KEM_ml_kem_768;SIG_ml_dsa_44",
        "-DOQS_USE_OPENSSL=OFF",
        "-DCMAKE_BUILD_TYPE=Debug",
        f"-DCMAKE_C_FLAGS=-O1 -g -fno-omit-frame-pointer -fsanitize=address,undefined {EXPERIMENTAL_DEFINES}",
        "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined",
    ], cwd=ROOT)

    run_cmd([
        "cmake",
        "--build", str(ASAN_BUILD),
        f"-j{os.cpu_count() or 2}",
    ], cwd=ROOT)


def build_valgrind() -> None:
    if VALGRIND_LIB.exists():
        print(f"Valgrind build already exists: {VALGRIND_LIB}")
        return

    run_cmd([
        "cmake",
        "-S", str(ROOT),
        "-B", str(VALGRIND_BUILD),
        "-DBUILD_SHARED_LIBS=OFF",
        "-DOQS_MINIMAL_BUILD=KEM_ml_kem_768;SIG_ml_dsa_44",
        "-DOQS_USE_OPENSSL=OFF",
        "-DCMAKE_BUILD_TYPE=Debug",
        f"-DCMAKE_C_FLAGS=-O0 -g -fno-omit-frame-pointer {EXPERIMENTAL_DEFINES}",
    ], cwd=ROOT)

    run_cmd([
        "cmake",
        "--build", str(VALGRIND_BUILD),
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


def choose_symbol(symbols: list[str], *, kind: str, role: str) -> str:
    candidates: list[str] = []

    for sym in symbols:
        if sym.startswith("__odr_asan."):
            continue

        s = norm(sym)

        if "workspace" not in s:
            continue
        if "lifecycle" not in s:
            continue

        if kind == "mlkem":
            if not (("mlkem" in s or "ml_kem" in s) and "768" in s and "v29" in s):
                continue
        elif kind == "mldsa":
            if not (("mldsa" in s or "ml_dsa" in s or "mld" in s) and "44" in s and "v24" in s):
                continue
        else:
            raise ValueError(kind)

        if role == "bytes":
            if s.endswith("_bytes"):
                candidates.append(sym)
        elif role == "setter":
            if "set" in s and not s.endswith("_bytes"):
                candidates.append(sym)
        else:
            raise ValueError(role)

    candidates = sorted(set(candidates), key=lambda x: (len(x), x))

    preferred = [c for c in candidates if "_X86_64_" in c]
    if preferred:
        candidates = preferred

    if not candidates:
        raise SystemExit(f"could not find {kind} {role} symbol in {SYMBOL_LOG}")

    if len(candidates) > 1:
        print(f"multiple {kind} {role} candidates found; using first:")
        for c in candidates:
            print(f"  {c}")

    return candidates[0]


def generate_workspace_header() -> tuple[str, str, str, str]:
    symbols = nm_symbols(ASAN_LIB)
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
        lines = [f"static inline size_t v34_{name}_workspace_need(void) {{", "    size_t n = 0;"]
        for b, _ in pairs:
            lines.append(f"    n = v34_max_size_t(n, {b}());")
        lines.append("    return n;")
        lines.append("}")
        return "\n".join(lines)

    def make_set_func(name: str, pairs: list[tuple[str, str]]) -> str:
        lines = [
            f"static inline int v34_{name}_workspace_set(void *ptr) {{",
            f"    const size_t n = v34_{name}_workspace_need();",
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
        "static inline size_t v34_max_size_t(size_t a, size_t b) {",
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

    return mlkem_pairs[0][0], mlkem_pairs[0][1], mldsa_pairs[0][0], mldsa_pairs[0][1]


def compile_harnesses() -> None:
    common_includes = [
        "-I", str(ASAN_BUILD / "include"),
        "-I", str(ROOT / "include"),
        "-I", str(EXP_DIR),
    ]

    run_cmd([
        "cc",
        "-std=c11",
        "-O1",
        "-g",
        "-fno-omit-frame-pointer",
        "-fsanitize=address,undefined",
        "-Wall",
        "-Wextra",
        *common_includes,
        str(SRC),
        "-o", str(ASAN_BIN),
        "-Wl,--start-group",
        str(ASAN_LIB),
        "-Wl,--end-group",
        "-pthread",
        "-lm",
        "-ldl",
        "-fsanitize=address,undefined",
    ], cwd=ROOT)

    valgrind_includes = [
        "-I", str(VALGRIND_BUILD / "include"),
        "-I", str(ROOT / "include"),
        "-I", str(EXP_DIR),
    ]

    run_cmd([
        "cc",
        "-std=c11",
        "-O0",
        "-g",
        "-fno-omit-frame-pointer",
        "-Wall",
        "-Wextra",
        *valgrind_includes,
        str(SRC),
        "-o", str(VALGRIND_BIN),
        "-Wl,--start-group",
        str(VALGRIND_LIB),
        "-Wl,--end-group",
        "-pthread",
        "-lm",
        "-ldl",
    ], cwd=ROOT)


def parse_case_rows(output: str, tool: str, tool_clean: bool) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for line in output.splitlines():
        if not line.startswith("V34_CASE,"):
            continue

        parts = line.strip().split(",")
        if len(parts) != 6:
            continue

        _, case_name, iterations, passed, failed, case_status = parts

        final_status = "PASS" if tool_clean and case_status == "PASS" else "FAIL"

        rows.append({
            "tool": tool,
            "case": case_name,
            "iterations": iterations,
            "passed": passed,
            "failed": failed,
            "status": final_status,
            "notes": "clean" if final_status == "PASS" else "check log",
        })

    return rows


def run_asan(iterations: int) -> list[dict[str, str]]:
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=1:halt_on_error=1:strict_string_checks=1:check_initialization_order=1"
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"

    proc = run_cmd_no_raise([
        str(ASAN_BIN),
        str(iterations),
    ], cwd=ROOT, env=env)

    ASAN_LOG.write_text(proc.stdout, encoding="utf-8")

    bad_markers = [
        "ERROR: AddressSanitizer",
        "ERROR: LeakSanitizer",
        "runtime error:",
        "UndefinedBehaviorSanitizer",
    ]

    clean = proc.returncode == 0 and not any(marker in proc.stdout for marker in bad_markers)

    return parse_case_rows(proc.stdout, "ASan+UBSan", clean)


def run_valgrind(iterations: int) -> list[dict[str, str]]:
    if shutil.which("valgrind") is None:
        raise SystemExit("valgrind not found. Install it with: sudo apt install -y valgrind")

    proc = run_cmd_no_raise([
        "valgrind",
        "--error-exitcode=99",
        "--leak-check=full",
        "--show-leak-kinds=definite,indirect,possible",
        "--errors-for-leak-kinds=definite,indirect,possible",
        "--track-origins=yes",
        str(VALGRIND_BIN),
        str(iterations),
    ], cwd=ROOT)

    VALGRIND_LOG.write_text(proc.stdout, encoding="utf-8")

    clean = proc.returncode == 0 and "ERROR SUMMARY: 0 errors" in proc.stdout

    return parse_case_rows(proc.stdout, "Valgrind", clean)


def write_csv(rows: list[dict[str, str]]) -> None:
    fields = ["tool", "case", "iterations", "passed", "failed", "status", "notes"]
    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    BUILD_LOG.write_text("", encoding="utf-8")

    asan_iterations = int(os.environ.get("V34_ASAN_ITERATIONS", "100"))
    valgrind_iterations = int(os.environ.get("V34_VALGRIND_ITERATIONS", "10"))

    build_asan_ubsan()
    build_valgrind()
    generate_workspace_header()
    compile_harnesses()

    rows: list[dict[str, str]] = []
    rows.extend(run_asan(asan_iterations))
    rows.extend(run_valgrind(valgrind_iterations))

    write_csv(rows)

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    failed = total - passed

    print(f"v34 summary: total_rows={total} pass_rows={passed} fail_rows={failed}")

    if failed != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
