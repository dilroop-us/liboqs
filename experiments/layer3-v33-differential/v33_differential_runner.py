#!/usr/bin/env python3
from pathlib import Path
import csv
import os
import re
import shutil
import subprocess
import sys

ROOT = Path.home() / "pqc/liboqs"
EXP = ROOT / "experiments/layer3-v33-differential"
RESULTS = ROOT / "layer3-results"

BASELINE_SRC = Path(os.environ.get("V33_BASELINE_SRC", str(Path.home() / "pqc/liboqs-v33-baseline")))
BASELINE_BUILD = Path(os.environ.get("V33_BASELINE_BUILD", str(BASELINE_SRC / "build-v33-baseline-reference")))
OPT_BUILD = Path(os.environ.get("V33_OPT_BUILD", str(ROOT / "build-v29-mlkem-lifecycle-workspace")))

SRC = EXP / "v33_differential_harness.c"
GEN_H = EXP / "v33_workspace_setup.generated.h"

BASELINE_BIN = RESULTS / "v33_differential_baseline_harness"
OPT_BIN = RESULTS / "v33_differential_optimized_harness"

CSV_OUT = RESULTS / "v33_differential.csv"
BUILD_LOG = RESULTS / "v33_build.log"
RUN_LOG = RESULTS / "v33_differential_run.log"
SYMS_FILE = RESULTS / "v33_lifecycle_symbols.txt"
VECTORS = RESULTS / "v33-vectors"

RESULT_RE = re.compile(r"^V33_RESULT,([^,]+),(\d+),(\d+),(\d+),(PASS|FAIL)$")


def log(msg: str) -> None:
    print(msg)
    with RUN_LOG.open("a") as f:
        f.write(msg + "\n")


def run(cmd, *, cwd=None, env=None, build_log=False, allow_fail=False):
    target_log = BUILD_LOG if build_log else RUN_LOG

    with target_log.open("a") as f:
        f.write("\n$ " + " ".join(map(str, cmd)) + "\n")

    proc = subprocess.run(
        list(map(str, cmd)),
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    with target_log.open("a") as f:
        f.write(proc.stdout)

    if proc.returncode != 0 and not allow_fail:
        print(proc.stdout)
        raise SystemExit(f"command failed: {' '.join(map(str, cmd))}")

    return proc


def find_liboqs(build_dir: Path) -> Path:
    candidates = [
        build_dir / "lib/liboqs.a",
        build_dir / "liboqs.a",
    ]

    for c in candidates:
        if c.exists():
            return c

    raise SystemExit(f"liboqs.a not found in {build_dir}")


def ensure_baseline_build() -> None:
    lib = None

    try:
        lib = find_liboqs(BASELINE_BUILD)
    except SystemExit:
        lib = None

    if lib is not None:
        return

    if not BASELINE_SRC.exists():
        raise SystemExit(f"baseline source missing: {BASELINE_SRC}")

    run(
        [
            "cmake",
            "-S",
            BASELINE_SRC,
            "-B",
            BASELINE_BUILD,
            "-DBUILD_SHARED_LIBS=OFF",
        ],
        build_log=True,
    )

    run(
        [
            "cmake",
            "--build",
            BASELINE_BUILD,
            "-j",
            str(os.cpu_count() or 2),
        ],
        build_log=True,
    )


def collect_symbols(lib: Path) -> list[str]:
    proc = run(
        ["nm", "-g", "--defined-only", lib],
        build_log=True,
        allow_fail=True,
    )

    symbols = []

    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and len(parts[-2]) == 1:
            symbols.append(parts[-1])

    symbols = sorted(set(symbols))
    SYMS_FILE.write_text("\n".join(symbols) + "\n")
    return symbols


def collect_pairs(symbols: list[str], scheme: str) -> list[tuple[str, str]]:
    if scheme == "mlkem":
        candidates = [
            s for s in symbols
            if "MLKEM" in s and "768" in s and "v29" in s and "lifecycle" in s and s.endswith("_bytes")
        ]
    else:
        candidates = [
            s for s in symbols
            if ("MLDSA" in s or "ML_DSA" in s or "MLD" in s)
            and "44" in s and "v24" in s and "lifecycle" in s and s.endswith("_bytes")
        ]

    pairs = []

    symbol_set = set(symbols)

    for b in candidates:
        setter = b[:-len("_bytes")] + "_set"
        if setter in symbol_set:
            pairs.append((b, setter))

    return pairs


def generate_workspace_header(opt_lib: Path) -> None:
    symbols = collect_symbols(opt_lib)
    mlkem_pairs = collect_pairs(symbols, "mlkem")
    mldsa_pairs = collect_pairs(symbols, "mldsa")

    if not mlkem_pairs:
        raise SystemExit("no ML-KEM v29 workspace symbols found")

    if not mldsa_pairs:
        raise SystemExit("no ML-DSA v24 workspace symbols found")

    lines = []
    lines.append("#ifndef V33_WORKSPACE_SETUP_GENERATED_H")
    lines.append("#define V33_WORKSPACE_SETUP_GENERATED_H")
    lines.append("")
    lines.append("#include <stddef.h>")
    lines.append("")

    for b, s in mlkem_pairs + mldsa_pairs:
        lines.append(f"extern size_t {b}(void);")
        lines.append(f"extern void {s}(void *);")

    lines.append("")
    lines.append("static size_t v33_mlkem_workspace_need(void) {")
    lines.append("    size_t need = 0;")
    lines.append("    size_t n = 0;")
    for b, _ in mlkem_pairs:
        lines.append(f"    n = {b}();")
        lines.append("    if (n > need) { need = n; }")
    lines.append("    return need;")
    lines.append("}")
    lines.append("")

    lines.append("static int v33_mlkem_workspace_set(void *workspace, size_t cap) {")
    lines.append("    size_t need = v33_mlkem_workspace_need();")
    lines.append("    if (workspace == 0 || cap < need) { return -1; }")
    for _, s in mlkem_pairs:
        lines.append(f"    {s}(workspace);")
    lines.append("    return 0;")
    lines.append("}")
    lines.append("")

    lines.append("static size_t v33_mldsa_workspace_need(void) {")
    lines.append("    size_t need = 0;")
    lines.append("    size_t n = 0;")
    for b, _ in mldsa_pairs:
        lines.append(f"    n = {b}();")
        lines.append("    if (n > need) { need = n; }")
    lines.append("    return need;")
    lines.append("}")
    lines.append("")

    lines.append("static int v33_mldsa_workspace_set(void *workspace, size_t cap) {")
    lines.append("    size_t need = v33_mldsa_workspace_need();")
    lines.append("    if (workspace == 0 || cap < need) { return -1; }")
    for _, s in mldsa_pairs:
        lines.append(f"    {s}(workspace);")
    lines.append("    return 0;")
    lines.append("}")
    lines.append("")

    lines.append("#endif")
    lines.append("")

    GEN_H.write_text("\n".join(lines))

    with BUILD_LOG.open("a") as f:
        f.write("\nWorkspace symbol pairs:\n")
        f.write("MLKEM_PAIRS=" + " ".join(f"{b}:{s}" for b, s in mlkem_pairs) + "\n")
        f.write("MLDSA_PAIRS=" + " ".join(f"{b}:{s}" for b, s in mldsa_pairs) + "\n")


def compile_harnesses() -> None:
    baseline_lib = find_liboqs(BASELINE_BUILD)
    opt_lib = find_liboqs(OPT_BUILD)

    generate_workspace_header(opt_lib)

    baseline_include_args = []

    if (BASELINE_BUILD / "include").exists():
        baseline_include_args += ["-I", BASELINE_BUILD / "include"]

    baseline_include_args += ["-I", BASELINE_SRC / "include"]
    baseline_include_args += ["-I", EXP]

    opt_include_args = []

    if (OPT_BUILD / "include").exists():
        opt_include_args += ["-I", OPT_BUILD / "include"]

    opt_include_args += ["-I", ROOT / "include"]
    opt_include_args += ["-I", EXP]

    common = [
        "cc",
        "-std=c11",
        "-O2",
        "-Wall",
        "-Wextra",
    ]

    run(
        common
        + baseline_include_args
        + [
            SRC,
            "-o",
            BASELINE_BIN,
            "-Wl,--start-group",
            baseline_lib,
            "-Wl,--end-group",
            "-pthread",
            "-lm",
            "-ldl",
        ],
        build_log=True,
    )

    run(
        common
        + [
            "-DV33_OPTIMIZED=1",
        ]
        + opt_include_args
        + [
            SRC,
            "-o",
            OPT_BIN,
            "-Wl,--start-group",
            opt_lib,
            "-Wl,--end-group",
            "-pthread",
            "-lm",
            "-ldl",
        ],
        build_log=True,
    )


def run_case(test, producer, consumer, binary, mode, vector, iterations, notes):
    env = os.environ.copy()
    env["V33_RNG_SEED"] = "layer3-v33-differential-fixed-seed"

    proc = run(
        [
            binary,
            mode,
            vector,
            str(iterations),
        ],
        env=env,
        allow_fail=True,
    )

    result = None

    for line in proc.stdout.splitlines():
        m = RESULT_RE.match(line.strip())
        if m:
            result = m

    if result is None:
        return {
            "test": test,
            "producer": producer,
            "consumer": consumer,
            "operation": mode,
            "iterations": str(iterations),
            "passed": "0",
            "failed": str(iterations),
            "status": "FAIL",
            "notes": notes + "; no V33_RESULT line",
        }

    _, actual_iterations, passed, failed, status = result.groups()

    if proc.returncode != 0:
        status = "FAIL"

    return {
        "test": test,
        "producer": producer,
        "consumer": consumer,
        "operation": mode,
        "iterations": actual_iterations,
        "passed": passed,
        "failed": failed,
        "status": status,
        "notes": notes,
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    VECTORS.mkdir(parents=True, exist_ok=True)

    BUILD_LOG.write_text("")
    RUN_LOG.write_text("")

    ensure_baseline_build()
    compile_harnesses()

    iterations = int(os.environ.get("V33_ITERATIONS", "100"))

    baseline_mlkem = VECTORS / "baseline_mlkem.bin"
    opt_mlkem = VECTORS / "optimized_mlkem.bin"
    baseline_mldsa = VECTORS / "baseline_mldsa.bin"
    opt_mldsa = VECTORS / "optimized_mldsa.bin"
    baseline_combined = VECTORS / "baseline_combined.bin"
    opt_combined = VECTORS / "optimized_combined.bin"

    rows = []

    rows.append(run_case(
        "baseline_mlkem_generate",
        "baseline",
        "none",
        BASELINE_BIN,
        "mlkem_gen",
        baseline_mlkem,
        iterations,
        "baseline generates ML-KEM vectors",
    ))

    rows.append(run_case(
        "baseline_mlkem_to_optimized",
        "baseline",
        "optimized",
        OPT_BIN,
        "mlkem_consume",
        baseline_mlkem,
        iterations,
        "optimized consumes baseline ML-KEM vectors",
    ))

    rows.append(run_case(
        "optimized_mlkem_generate",
        "optimized",
        "none",
        OPT_BIN,
        "mlkem_gen",
        opt_mlkem,
        iterations,
        "optimized generates ML-KEM vectors",
    ))

    rows.append(run_case(
        "optimized_mlkem_to_baseline",
        "optimized",
        "baseline",
        BASELINE_BIN,
        "mlkem_consume",
        opt_mlkem,
        iterations,
        "baseline consumes optimized ML-KEM vectors",
    ))

    rows.append(run_case(
        "baseline_mldsa_generate",
        "baseline",
        "none",
        BASELINE_BIN,
        "mldsa_gen",
        baseline_mldsa,
        iterations,
        "baseline generates ML-DSA signatures",
    ))

    rows.append(run_case(
        "baseline_mldsa_to_optimized",
        "baseline",
        "optimized",
        OPT_BIN,
        "mldsa_consume",
        baseline_mldsa,
        iterations,
        "optimized verifies and signs using baseline ML-DSA vectors",
    ))

    rows.append(run_case(
        "optimized_mldsa_generate",
        "optimized",
        "none",
        OPT_BIN,
        "mldsa_gen",
        opt_mldsa,
        iterations,
        "optimized generates ML-DSA signatures",
    ))

    rows.append(run_case(
        "optimized_mldsa_to_baseline",
        "optimized",
        "baseline",
        BASELINE_BIN,
        "mldsa_consume",
        opt_mldsa,
        iterations,
        "baseline verifies and signs using optimized ML-DSA vectors",
    ))

    rows.append(run_case(
        "baseline_combined_generate",
        "baseline",
        "none",
        BASELINE_BIN,
        "combined_gen",
        baseline_combined,
        iterations,
        "baseline generates combined KEM transcript and signature vectors",
    ))

    rows.append(run_case(
        "baseline_combined_to_optimized",
        "baseline",
        "optimized",
        OPT_BIN,
        "combined_consume",
        baseline_combined,
        iterations,
        "optimized consumes baseline combined vectors",
    ))

    rows.append(run_case(
        "optimized_combined_generate",
        "optimized",
        "none",
        OPT_BIN,
        "combined_gen",
        opt_combined,
        iterations,
        "optimized generates combined KEM transcript and signature vectors",
    ))

    rows.append(run_case(
        "optimized_combined_to_baseline",
        "optimized",
        "baseline",
        BASELINE_BIN,
        "combined_consume",
        opt_combined,
        iterations,
        "baseline consumes optimized combined vectors",
    ))

    with CSV_OUT.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "test",
                "producer",
                "consumer",
                "operation",
                "iterations",
                "passed",
                "failed",
                "status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    passed_rows = sum(1 for r in rows if r["status"] == "PASS")
    failed_rows = total - passed_rows

    log("")
    log(f"v33 summary: total_rows={total} pass_rows={passed_rows} fail_rows={failed_rows}")

    if failed_rows:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
