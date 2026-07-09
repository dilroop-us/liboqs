#!/usr/bin/env python3

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path.home() / "pqc" / "liboqs"
EXP_DIR = ROOT / "experiments" / "layer3-v37-build-matrix"
RESULTS = ROOT / "layer3-results"
LOG_DIR = RESULTS / "v37-build-logs"

SRC = EXP_DIR / "v37_build_matrix_harness.c"
HEADER = EXP_DIR / "v37_workspace_setup.generated.h"

CSV_OUT = RESULTS / "v37_build_matrix.csv"
REPORT_MD = RESULTS / "v37_build_matrix_report.md"

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

MATRIX = [
    {
        "case": "release_static_o3",
        "build_type": "Release",
        "cflags_profile": "O3",
        "cflags": "-O3 -g0 -fno-omit-frame-pointer",
    },
    {
        "case": "relwithdebinfo_static_o2",
        "build_type": "RelWithDebInfo",
        "cflags_profile": "O2_debug",
        "cflags": "-O2 -g -fno-omit-frame-pointer",
    },
    {
        "case": "debug_static_o0",
        "build_type": "Debug",
        "cflags_profile": "O0_debug",
        "cflags": "-O0 -g3 -fno-omit-frame-pointer",
    },
    {
        "case": "size_static_os",
        "build_type": "Release",
        "cflags_profile": "Os",
        "cflags": "-Os -g0 -fno-omit-frame-pointer",
    },
]


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def run_cmd(cmd: list[str], *, cwd: Path | None = None, log: Path) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    with log.open("a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join(cmd) + "\n")
        f.write(proc.stdout)

    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}")

    return proc


def norm(s: str) -> str:
    return s.lower().replace("-", "_")


def build_dir(case: str) -> Path:
    return ROOT / f"build-v37-matrix-{case}"


def lib_path(build: Path) -> Path:
    return build / "lib" / "liboqs.a"


def harness_path(case: str) -> Path:
    return RESULTS / f"v37_build_matrix_harness_{case}"


def build_case(cfg: dict[str, str], force: bool, log: Path) -> Path:
    case = cfg["case"]
    build = build_dir(case)
    lib = lib_path(build)

    if force and build.exists():
        shutil.rmtree(build)

    if lib.exists():
        print(f"v37 build already exists for {case}: {lib}")
        return lib

    c_flags = f"{cfg['cflags']} {EXPERIMENTAL_DEFINES}"

    run_cmd([
        "cmake",
        "-S", str(ROOT),
        "-B", str(build),
        "-DBUILD_SHARED_LIBS=OFF",
        "-DOQS_MINIMAL_BUILD=KEM_ml_kem_768;SIG_ml_dsa_44",
        "-DOQS_USE_OPENSSL=OFF",
        f"-DCMAKE_BUILD_TYPE={cfg['build_type']}",
        f"-DCMAKE_C_FLAGS={c_flags}",
    ], cwd=ROOT, log=log)

    run_cmd([
        "cmake",
        "--build", str(build),
        f"-j{os.cpu_count() or 2}",
    ], cwd=ROOT, log=log)

    if not lib.exists():
        raise RuntimeError(f"liboqs.a not found after build: {lib}")

    return lib


def nm_symbols(lib: Path, log: Path, symbol_log: Path) -> list[str]:
    proc = run_cmd([
        "nm",
        "-g",
        "--defined-only",
        str(lib),
    ], cwd=ROOT, log=log)

    symbol_log.write_text(proc.stdout, encoding="utf-8")

    symbols: list[str] = []
    for line in proc.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            symbols.append(parts[-1])
    return symbols


def generate_workspace_header(symbols: list[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
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
            raise RuntimeError(f"could not find {kind} lifecycle workspace byte/setter pair")

        return pairs

    mlkem_pairs = collect_pairs("mlkem")
    mldsa_pairs = collect_pairs("mldsa")

    decls: list[str] = []
    for b, setter in mlkem_pairs + mldsa_pairs:
        decls.append(f"extern size_t {b}(void);")
        decls.append(f"extern int {setter}(void *, size_t);")

    def make_need_func(name: str, pairs: list[tuple[str, str]]) -> str:
        lines = [f"static inline size_t v37_{name}_workspace_need(void) {{", "    size_t n = 0;"]
        for b, _ in pairs:
            lines.append(f"    n = v37_max_size_t(n, {b}());")
        lines.append("    return n;")
        lines.append("}")
        return "\n".join(lines)

    def make_set_func(name: str, pairs: list[tuple[str, str]]) -> str:
        lines = [
            f"static inline int v37_{name}_workspace_set(void *ptr) {{",
            "    int ok = 0;",
        ]

        # Build-matrix validation may expose both C and X86_64 lifecycle symbols.
        # Accept workspace setup if at least one implementation setter accepts
        # its own reported workspace size. Correctness rows then validate the
        # active implementation path.
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
        "static inline size_t v37_max_size_t(size_t a, size_t b) {",
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
    return mlkem_pairs, mldsa_pairs


def compile_harness(cfg: dict[str, str], build: Path, lib: Path, log: Path) -> Path:
    case = cfg["case"]
    bin_path = harness_path(case)

    includes = [
        "-I", str(build / "include"),
        "-I", str(ROOT / "include"),
        "-I", str(EXP_DIR),
    ]

    run_cmd([
        "cc",
        "-std=c11",
        cfg["cflags"].split()[0],
        "-g",
        "-fno-omit-frame-pointer",
        "-Wall",
        "-Wextra",
        *includes,
        str(SRC),
        "-o", str(bin_path),
        "-Wl,--start-group",
        str(lib),
        "-Wl,--end-group",
        "-lm",
        "-ldl",
    ], cwd=ROOT, log=log)

    return bin_path


def run_harness(cfg: dict[str, str], bin_path: Path, iterations: int, log: Path) -> str:
    case = cfg["case"]

    proc = subprocess.run(
        [str(bin_path), case, str(iterations)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    with log.open("a", encoding="utf-8") as f:
        f.write("\n$ " + " ".join([str(bin_path), case, str(iterations)]) + "\n")
        f.write(proc.stdout)

    run_log = LOG_DIR / f"{case}.run.log"
    run_log.write_text(proc.stdout, encoding="utf-8")

    if proc.returncode != 0:
        raise RuntimeError(f"v37 harness failed for {case} with exit code {proc.returncode}")

    return proc.stdout


def parse_workspace(output: str, build_case: str, name: str) -> int:
    prefix = f"V37_WORKSPACE,{build_case},{name},"
    for line in output.splitlines():
        if line.startswith(prefix):
            return int(line.split(",")[3])
    return 0


def parse_case_rows(cfg: dict[str, str], output: str, mlkem_pairs: list[tuple[str, str]], mldsa_pairs: list[tuple[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    build_case = cfg["case"]

    mlkem_ws = parse_workspace(output, build_case, "ML-KEM")
    mldsa_ws = parse_workspace(output, build_case, "ML-DSA")
    combined_ws = parse_workspace(output, build_case, "COMBINED")

    for line in output.splitlines():
        if not line.startswith("V37_CASE,"):
            continue

        parts = line.split(",", 7)
        if len(parts) != 8:
            continue

        (
            _tag,
            case,
            component,
            iterations,
            passed,
            failed,
            status,
            notes,
        ) = parts

        rows.append({
            "build_case": case,
            "build_type": cfg["build_type"],
            "cflags_profile": cfg["cflags_profile"],
            "linkage": "static",
            "mlkem_workspace_bytes": str(mlkem_ws),
            "mldsa_workspace_bytes": str(mldsa_ws),
            "combined_workspace_bytes": str(combined_ws),
            "mlkem_symbol_pairs": str(len(mlkem_pairs)),
            "mldsa_symbol_pairs": str(len(mldsa_pairs)),
            "component": component,
            "iterations": iterations,
            "passed": passed,
            "failed": failed,
            "status": status,
            "notes": notes,
        })

    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "build_case",
        "build_type",
        "cflags_profile",
        "linkage",
        "mlkem_workspace_bytes",
        "mldsa_workspace_bytes",
        "combined_workspace_bytes",
        "mlkem_symbol_pairs",
        "mldsa_symbol_pairs",
        "component",
        "iterations",
        "passed",
        "failed",
        "status",
        "notes",
    ]

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict[str, str]]) -> None:
    build_cases = []
    for r in rows:
        if r["build_case"] not in build_cases:
            build_cases.append(r["build_case"])

    total_rows = len(rows)
    pass_rows = sum(1 for r in rows if r["status"] == "PASS")
    fail_rows = sum(1 for r in rows if r["status"] == "FAIL")
    overall = "PASS" if total_rows > 0 and fail_rows == 0 else "FAIL"

    lines: list[str] = []

    lines.append("# Layer 3 v37: Build Matrix Validation")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("v37 validates whether the optimized ML-KEM-768 and ML-DSA-44 lifecycle-workspace build compiles and passes core correctness checks across selected build configurations.")
    lines.append("")
    lines.append("The matrix uses static minimal liboqs builds for:")
    lines.append("")
    lines.append("- ML-KEM-768 with v29 lifecycle workspace")
    lines.append("- ML-DSA-44 with v24 lifecycle workspace")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| build cases | {len(build_cases)} |")
    lines.append(f"| total result rows | {total_rows} |")
    lines.append(f"| PASS rows | {pass_rows} |")
    lines.append(f"| FAIL rows | {fail_rows} |")
    lines.append(f"| overall v37 status | {overall} |")
    lines.append("")
    lines.append("## Build matrix results")
    lines.append("")
    lines.append("| Build case | Build type | C flags profile | Linkage | ML-KEM symbols | ML-DSA symbols | ML-KEM ws | ML-DSA ws | Combined ws | Status |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---|")

    for case in build_cases:
        case_rows = [r for r in rows if r["build_case"] == case]
        first = case_rows[0]
        status = "PASS" if all(r["status"] == "PASS" for r in case_rows) else "FAIL"

        lines.append(
            f"| {case} | {first['build_type']} | {first['cflags_profile']} | {first['linkage']} | "
            f"{first['mlkem_symbol_pairs']} | {first['mldsa_symbol_pairs']} | "
            f"{first['mlkem_workspace_bytes']} | {first['mldsa_workspace_bytes']} | {first['combined_workspace_bytes']} | {status} |"
        )

    lines.append("")
    lines.append("## Component-level results")
    lines.append("")
    lines.append("| Build case | Component | Iterations | Passed | Failed | Status | Notes |")
    lines.append("|---|---|---:|---:|---:|---|---|")

    for r in rows:
        lines.append(
            f"| {r['build_case']} | {r['component']} | {r['iterations']} | {r['passed']} | {r['failed']} | {r['status']} | {r['notes']} |"
        )

    lines.append("")
    lines.append("## What v37 checks")
    lines.append("")
    lines.append("| Area | Check |")
    lines.append("|---|---|")
    lines.append("| Build coverage | selected Release, RelWithDebInfo, Debug, and size-focused static builds |")
    lines.append("| Symbol coverage | ML-KEM and ML-DSA lifecycle workspace byte/setter symbols are discovered per build |")
    lines.append("| Harness compile | v37 correctness harness compiles against each selected build |")
    lines.append("| ML-KEM correctness | keypair, encaps, decaps, shared-secret equality |")
    lines.append("| ML-DSA correctness | keypair, sign, verify, reject modified message/signature |")
    lines.append("| Combined flow | ML-KEM transcript construction and ML-DSA signature verification |")
    lines.append("")
    lines.append("## Claims supported by v37")
    lines.append("")
    lines.append("| Claim | Status |")
    lines.append("|---|---|")
    lines.append("| optimized lifecycle-workspace build works across selected build configurations | supported if PASS |")
    lines.append("| lifecycle workspace symbols are present across selected configurations | supported if PASS |")
    lines.append("| core ML-KEM, ML-DSA, and combined correctness checks pass across the matrix | supported if PASS |")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- v37 does not test every compiler.")
    lines.append("- v37 does not test every architecture.")
    lines.append("- v37 does not test every liboqs CMake option.")
    lines.append("- v37 does not test Rust FFI.")
    lines.append("- v37 does not prove constant-time behavior.")
    lines.append("- v37 does not prove production portability.")
    lines.append("")
    lines.append("## Next")
    lines.append("")
    lines.append("v38 should perform timing / constant-time-style leakage validation.")
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    force = os.environ.get("V37_FORCE_REBUILD", "0") == "1"
    iterations = env_int("V37_ITERATIONS", 20)

    all_rows: list[dict[str, str]] = []

    for cfg in MATRIX:
        case = cfg["case"]
        print(f"=== v37 build case: {case} ===")

        log = LOG_DIR / f"{case}.build.log"
        symbol_log = LOG_DIR / f"{case}.symbols.txt"
        log.write_text("", encoding="utf-8")

        lib = build_case(cfg, force, log)
        build = build_dir(case)

        symbols = nm_symbols(lib, log, symbol_log)
        mlkem_pairs, mldsa_pairs = generate_workspace_header(symbols)

        print(f"  ML-KEM symbol pairs: {len(mlkem_pairs)}")
        print(f"  ML-DSA symbol pairs: {len(mldsa_pairs)}")

        bin_path = compile_harness(cfg, build, lib, log)
        output = run_harness(cfg, bin_path, iterations, log)

        rows = parse_case_rows(cfg, output, mlkem_pairs, mldsa_pairs)
        all_rows.extend(rows)

    write_csv(all_rows)
    write_report(all_rows)

    total = len(all_rows)
    passed = sum(1 for r in all_rows if r["status"] == "PASS")
    failed = sum(1 for r in all_rows if r["status"] == "FAIL")

    print(f"v37 summary: total_rows={total} pass_rows={passed} fail_rows={failed}")
    print(f"wrote {CSV_OUT}")
    print(f"wrote {REPORT_MD}")

    if failed != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
