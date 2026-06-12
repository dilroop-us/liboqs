#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

STACK_FILES = {
    "baseline": RESULTS / "v14_baseline_stack_usage.csv",
    "reduce_ram": RESULTS / "v14_reduce_ram_stack_usage.csv",
    "static_matrix": RESULTS / "v15_static_matrix_stack_usage.csv",
    "caller_matrix": RESULTS / "v16_caller_matrix_stack_usage.csv",
    "full_sign": RESULTS / "v17b_full_sign_workspace_stack_usage.csv",
    "workspace_sanitize": RESULTS / "v18_workspace_sanitize_stack_usage.csv",
}

PROFILE_NAMES = {
    "baseline": "Baseline",
    "reduce_ram": "Reduced-RAM",
    "static_matrix": "v15 static matrix",
    "caller_matrix": "v16 caller matrix",
    "full_sign": "v17b full sign workspace",
    "workspace_sanitize": "v18 sanitized workspace",
}


def normalize_function(fn: str) -> str:
    if fn.startswith("mld_compute_pack_t0_t1"):
        return "mld_compute_pack_t0_t1"
    return fn


def load_stack(path: Path):
    data = {}

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("variant") != "x86_64":
                continue

            fn = normalize_function(row["function"])
            data[fn] = max(data.get(fn, 0), int(row["bytes"]))

    return data


def find_stack_value(data, contains: str):
    vals = [size for fn, size in data.items() if contains in fn]
    return max(vals) if vals else 0


def effective_sign_stack(data):
    signature_internal = find_stack_value(data, "signature_internal")
    attempt = find_stack_value(data, "mld_attempt_signature_generation")
    return max(signature_internal, attempt)


def load_workspace_bytes(path: Path):
    out = {}

    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[row["profile"]] = {
                "kind": row["workspace_kind"],
                "bytes": int(row["bytes"]),
            }

    return out


def load_speed():
    speed = {}

    for path in [RESULTS / "v17b_speed.csv", RESULTS / "v18_speed.csv"]:
        if not path.exists():
            continue

        with path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                speed[(row["profile"], row["mode"])] = row["mean_us"]

    return speed


def load_bss():
    bss = {}

    path = RESULTS / "v17b_size.csv"
    if path.exists():
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) < 6 or not parts[0].isdigit():
                continue

            bss_value = int(parts[2])
            filename = parts[-1]

            if "v17b_baseline_profiler" in filename:
                bss["baseline"] = bss_value
            elif "v17b_reduce_ram_profiler" in filename:
                bss["reduce_ram"] = bss_value
            elif "v17b_static_matrix_profiler" in filename:
                bss["static_matrix"] = bss_value
            elif "v17b_caller_matrix_profiler" in filename:
                bss["caller_matrix"] = bss_value
            elif "v17b_full_sign_profiler" in filename:
                bss["full_sign"] = bss_value

    path = RESULTS / "v18_size.csv"
    if path.exists():
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) < 6 or not parts[0].isdigit():
                continue

            if "v18_workspace_sanitize_profiler" in parts[-1]:
                bss["workspace_sanitize"] = int(parts[2])

    return bss


def main() -> int:
    workspace = load_workspace_bytes(RESULTS / "v18_workspace_bytes.csv")
    speed = load_speed()
    bss = load_bss()

    rows = []

    for profile, path in STACK_FILES.items():
        stack = load_stack(path)

        sign_stack = effective_sign_stack(stack)
        verify_stack = find_stack_value(stack, "verify_internal")
        workspace_bytes = workspace.get(profile, {}).get("bytes", 0)
        bss_bytes = bss.get(profile, 0)

        rows.append({
            "profile": profile,
            "name": PROFILE_NAMES[profile],
            "sign_stack": sign_stack,
            "verify_stack": verify_stack,
            "workspace_kind": workspace.get(profile, {}).get("kind", "unknown"),
            "workspace_bytes": workspace_bytes,
            "bss": bss_bytes,
            "visible_memory": sign_stack + workspace_bytes + bss_bytes,
            "sign_us": speed.get((profile, "sig-sign"), "-"),
            "verify_us": speed.get((profile, "sig-verify"), "-"),
        })

    out = RESULTS / "v18_workspace_accounting_report.md"

    with out.open("w") as f:
        f.write("# Layer 3 v18 Workspace Accounting Report\n\n")
        f.write("v18 reports stack, caller workspace, BSS, and speed together.\n\n")

        f.write("## Main accounting table\n\n")
        f.write("| Profile | Sign hot stack B | Verify stack B | Caller workspace B | BSS B | Stack + workspace + BSS B | Sign us | Verify us | Workspace kind |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---:|---|\n")

        for row in rows:
            f.write(
                f"| {row['name']} | {row['sign_stack']} | {row['verify_stack']} | "
                f"{row['workspace_bytes']} | {row['bss']} | {row['visible_memory']} | "
                f"{row['sign_us']} | {row['verify_us']} | {row['workspace_kind']} |\n"
            )

        f.write("\n## Key observations\n\n")
        f.write("- Baseline is fast but stack-heavy.\n")
        f.write("- Reduced-RAM has low stack but much slower signing.\n")
        f.write("- v15 static matrix keeps speed but hides memory in BSS.\n")
        f.write("- v16 moves the 16 KB matrix into caller-owned workspace.\n")
        f.write("- v17b moves the 28 KB full signing workspace into caller-owned memory.\n")
        f.write("- v18 keeps the v17b workspace model and clears the workspace during cleanup.\n\n")

        f.write("## Security note\n\n")
        f.write("The v17b/v18 full signing workspace contains secret-derived buffers such as `s1hat`, `s2hat`, and `t0hat`. ")
        f.write("v18 adds an experimental sanitization path that clears the caller-provided workspace during cleanup.\n\n")

        f.write("## Tradeoff\n\n")
        f.write("v18 keeps the stack and BSS benefits of v17b, but the full-workspace sanitization adds runtime overhead. ")
        f.write("This is expected because the current sanitizer clears the full caller-provided signing workspace.\n\n")

        f.write("## Conclusion\n\n")
        f.write("v18 proves the real memory tradeoff: the optimization does not remove memory entirely. ")
        f.write("It converts hidden stack pressure into explicit caller-owned workspace memory, keeps BSS low, and adds cleanup for secret-derived workspace data.\n")

    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
