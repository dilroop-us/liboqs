#!/usr/bin/env python3

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
EXP_DIR = ROOT / "experiments" / "layer3-v38-timing-leakage"
RESULTS = ROOT / "layer3-results"

BUILD = ROOT / "build-v38-timing-leakage"
LIB = BUILD / "lib" / "liboqs.a"

SRC = EXP_DIR / "v38_timing_leakage_harness.c"
HEADER = EXP_DIR / "v38_workspace_setup.generated.h"
BIN = RESULTS / "v38_timing_leakage_harness"

BUILD_LOG = RESULTS / "v38_build.log"
RUN_LOG = RESULTS / "v38_timing_leakage_run.log"
SYMBOL_LOG = RESULTS / "v38_lifecycle_symbols.txt"
CSV_OUT = RESULTS / "v38_timing_leakage.csv"

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


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


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


def build_timing() -> None:
    force = os.environ.get("V38_FORCE_REBUILD", "0") == "1"

    if force and BUILD.exists():
        shutil.rmtree(BUILD)

    if LIB.exists():
        print(f"v38 timing build already exists: {LIB}")
        return

    c_flags = (
        "-O2 -g -fno-omit-frame-pointer "
        f"{EXPERIMENTAL_DEFINES}"
    )

    run_cmd([
        "cmake",
        "-S", str(ROOT),
        "-B", str(BUILD),
        "-DBUILD_SHARED_LIBS=OFF",
        "-DOQS_MINIMAL_BUILD=KEM_ml_kem_768;SIG_ml_dsa_44",
        "-DOQS_USE_OPENSSL=OFF",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        f"-DCMAKE_C_FLAGS={c_flags}",
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
        lines = [f"static inline size_t v38_{name}_workspace_need(void) {{", "    size_t n = 0;"]
        for b, _ in pairs:
            lines.append(f"    n = v38_max_size_t(n, {b}());")
        lines.append("    return n;")
        lines.append("}")
        return "\n".join(lines)

    def make_set_func(name: str, pairs: list[tuple[str, str]]) -> str:
        lines = [
            f"static inline int v38_{name}_workspace_set(void *ptr) {{",
            "    int ok = 0;",
        ]

        for bytes_fn, setter in pairs:
            lines.append(f"    if ({setter}(ptr, {bytes_fn}()) == 0) ok = 1;")

        lines.append("    return ok ? 0 : -1;")
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
        "static inline size_t v38_max_size_t(size_t a, size_t b) {",
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
        "-O2",
        "-g",
        "-fno-omit-frame-pointer",
        "-Wall",
        "-Wextra",
        *includes,
        str(SRC),
        "-o", str(BIN),
        "-Wl,--start-group",
        str(LIB),
        "-Wl,--end-group",
        "-lm",
        "-ldl",
    ], cwd=ROOT)


def run_harness(samples: int, warmup: int, threshold: float, batch: int) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [str(BIN), str(samples), str(warmup), str(threshold), str(batch)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    RUN_LOG.write_text(proc.stdout, encoding="utf-8")

    if proc.returncode != 0:
        print(proc.stdout)
        raise SystemExit(f"v38 harness failed with exit code {proc.returncode}")

    return proc


def parse_run_log(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for line in output.splitlines():
        if not line.startswith("V38_CASE,"):
            continue

        parts = line.split(",", 11)
        if len(parts) != 12:
            continue

        (
            _tag,
            name,
            samples,
            n0,
            n1,
            mean0_ns,
            mean1_ns,
            t_abs,
            threshold,
            exec_failures,
            status,
            notes,
        ) = parts

        rows.append({
            "case": name,
            "samples": samples,
            "class0_n": n0,
            "class1_n": n1,
            "class0_mean_ns": mean0_ns,
            "class1_mean_ns": mean1_ns,
            "welch_t_abs": t_abs,
            "threshold": threshold,
            "exec_failures": exec_failures,
            "status": status,
            "notes": notes,
        })

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case",
                "samples",
                "class0_n",
                "class1_n",
                "class0_mean_ns",
                "class1_mean_ns",
                "welch_t_abs",
                "threshold",
                "exec_failures",
                "status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return rows


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    BUILD_LOG.write_text("", encoding="utf-8")

    samples = env_int("V38_SAMPLES", 2000)
    warmup = env_int("V38_WARMUP", 100)
    threshold = env_float("V38_THRESHOLD", 4.5)
    batch = env_int("V38_BATCH", 1)

    build_timing()
    generate_workspace_header()
    compile_harness()

    proc = run_harness(samples, warmup, threshold, batch)
    rows = parse_run_log(proc.stdout)

    total = len(rows)
    passed = sum(1 for r in rows if r["status"] == "PASS")
    flagged = sum(1 for r in rows if r["status"] == "FLAG")
    failed = sum(1 for r in rows if r["status"] == "FAIL")

    print(f"v38 summary: total_rows={total} pass_rows={passed} flag_rows={flagged} fail_rows={failed}")

    if failed != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
