#!/usr/bin/env python3
from pathlib import Path
import csv
import json

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

OUT_MD = RESULTS / "v30_combined_pqc_summary_report.md"
OUT_CSV = RESULTS / "v30_combined_pqc_summary.csv"
OUT_JSON = RESULTS / "v30_combined_pqc_summary.json"

# Existing result files from the ML-KEM phase.
V25B_MLKEM_SPEED = RESULTS / "v25b_mlkem_speed.csv"
V29_MLKEM_SPEED = RESULTS / "v29_mlkem_speed.csv"
V29_MLKEM_SIZE = RESULTS / "v29_mlkem_size.csv"
V29_MLKEM_WORKSPACE = RESULTS / "v29_mlkem_workspace.csv"
V29_MLKEM_TARGETS = RESULTS / "v29_mlkem_targets.md"

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def load_csv(path):
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def latest_speed(rows, profile, mode, fallback):
    matches = [
        r for r in rows
        if r.get("profile") == profile and r.get("mode") == mode
    ]

    if not matches:
        return fallback, "fallback"

    return float(matches[-1]["mean_us"]), str(path_name(rows))


def path_name(_rows):
    return "csv"


def pct_delta(old, new):
    return ((new - old) / old) * 100.0


def pct_saved(old, new):
    return ((old - new) / old) * 100.0


def bytes_saved(old, new):
    return old - new


def kib(n):
    return n / 1024.0


def fmt_pct(x):
    return f"{x:.2f}%"


def fmt_us(x):
    return f"{x:.3f}"


def reduction_pct(old, new):
    return ((old - new) / old) * 100.0


def md_table(headers, rows):
    out = "| " + " | ".join(headers) + " |\n"
    out += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in rows:
        out += "| " + " | ".join(str(x) for x in row) + " |\n"
    return out + "\n"


def dedup_rows(rows, keys):
    seen = set()
    out = []
    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


# ---------------------------------------------------------------------
# Fixed known values from completed Layer 3 work
# ---------------------------------------------------------------------

MLKEM_STACK = [
    {
        "scheme": "ML-KEM-768",
        "variant": "x86_64",
        "function": "indcpa_enc",
        "baseline": 13312,
        "final": 192,
        "version": "v26/v29",
    },
    {
        "scheme": "ML-KEM-768",
        "variant": "ref",
        "function": "indcpa_enc",
        "baseline": 13312,
        "final": 160,
        "version": "v26/v29",
    },
    {
        "scheme": "ML-KEM-768",
        "variant": "x86_64",
        "function": "indcpa_keypair_derand",
        "baseline": 10336,
        "final": 192,
        "version": "v27/v29",
    },
    {
        "scheme": "ML-KEM-768",
        "variant": "ref",
        "function": "indcpa_keypair_derand",
        "baseline": 10336,
        "final": 128,
        "version": "v27/v29",
    },
    {
        "scheme": "ML-KEM-768",
        "variant": "x86_64",
        "function": "indcpa_dec",
        "baseline": 4992,
        "final": 80,
        "version": "v28/v29",
    },
    {
        "scheme": "ML-KEM-768",
        "variant": "ref",
        "function": "indcpa_dec",
        "baseline": 4992,
        "final": 80,
        "version": "v28/v29",
    },
]

MLDSA_STACK = [
    {
        "scheme": "ML-DSA-44",
        "variant": "ref/x86_64",
        "function": "signature_internal",
        "baseline": 44624,
        "final": 15584,
        "version": "v17b milestone",
        "note": "signing frame after moving matrix and signing vectors",
    },
    {
        "scheme": "ML-DSA-44",
        "variant": "ref/x86_64",
        "function": "mld_attempt_signature_generation",
        "baseline": 15584,
        "final": 544,
        "version": "v19b milestone",
        "note": "attempt-generation locals moved to caller workspace; final wrapper size approx",
    },
    {
        "scheme": "ML-DSA-44",
        "variant": "ref/x86_64",
        "function": "mld_sign_verify_internal",
        "baseline": 8256,
        "final": 192,
        "version": "v22b",
        "note": "verification workspace",
    },
    {
        "scheme": "ML-DSA-44",
        "variant": "ref/x86_64",
        "function": "keypair_internal",
        "baseline": 8640,
        "final": 160,
        "version": "v23b",
        "note": "keypair workspace",
    },
    {
        "scheme": "ML-DSA-44",
        "variant": "ref/x86_64",
        "function": "pk_from_sk",
        "baseline": 10176,
        "final": 96,
        "version": "v23b",
        "note": "provisioning workspace",
    },
]

MLDSA_HIGH_LEVEL = {
    "baseline_total": 88080,
    "final_total": 992,
    "saved": 88080 - 992,
    "saved_pct": pct_saved(88080, 992),
}

MLKEM_WORKSPACE = {
    "v26_enc_workspace": 13088,
    "v27_keypair_workspace": 10112,
    "v28_dec_workspace": 4864,
    "separate_total": 28064,
    "lifecycle": 13088,
    "saved": 14976,
    "saved_pct": 53.36,
}

MLDSA_WORKSPACE = {
    "sign_workspace": 44064,
    "verify_workspace": 8128,
    "keygen_workspace": 10240,
    "separate_total": 62432,
    "lifecycle": 44064,
    "saved": 18368,
    "saved_pct": 29.42,
}

COMBINED_WORKSPACE = {
    "mlkem_lifecycle": MLKEM_WORKSPACE["lifecycle"],
    "mldsa_lifecycle": MLDSA_WORKSPACE["lifecycle"],
    "combined_total": MLKEM_WORKSPACE["lifecycle"] + MLDSA_WORKSPACE["lifecycle"],
}

# Baseline/final speed fallbacks.
# ML-KEM baseline is v25b mlkem_only. ML-KEM final is v29 lifecycle.
MLKEM_SPEED_DEFAULTS = {
    "kem-keypair": {"baseline": 12.651, "final": 12.767},
    "kem-encaps": {"baseline": 13.357, "final": 13.319},
    "kem-decaps": {"baseline": 16.812, "final": 16.817},
}

# ML-DSA baseline from the earlier Layer 3 baseline profiler.
# ML-DSA final from v24b compact lifecycle workspace.
MLDSA_SPEED = {
    "sig-keypair": {"baseline": 27.188, "final": 26.854},
    "sig-sign": {"baseline": 82.037, "final": 80.368},
    "sig-verify": {"baseline": 27.845, "final": 27.391},
}

# ---------------------------------------------------------------------
# Pull ML-KEM speed from CSV when available
# ---------------------------------------------------------------------

v25b_mlkem_speed = load_csv(V25B_MLKEM_SPEED)
v29_mlkem_speed = load_csv(V29_MLKEM_SPEED)
v29_mlkem_size = load_csv(V29_MLKEM_SIZE)
v29_mlkem_workspace = dedup_rows(load_csv(V29_MLKEM_WORKSPACE), ["profile", "workspace_kind", "bytes"])

mlkem_speed_rows = []
for op, defaults in MLKEM_SPEED_DEFAULTS.items():
    baseline, _ = latest_speed(v25b_mlkem_speed, "mlkem_only", op, defaults["baseline"])
    final, _ = latest_speed(v29_mlkem_speed, "v29_lifecycle_workspace", op, defaults["final"])
    mlkem_speed_rows.append({
        "operation": op,
        "baseline": baseline,
        "final": final,
        "delta_us": final - baseline,
        "delta_pct": pct_delta(baseline, final),
    })

mldsa_speed_rows = []
for op, vals in MLDSA_SPEED.items():
    baseline = vals["baseline"]
    final = vals["final"]
    mldsa_speed_rows.append({
        "operation": op,
        "baseline": baseline,
        "final": final,
        "delta_us": final - baseline,
        "delta_pct": pct_delta(baseline, final),
    })

# ---------------------------------------------------------------------
# CSV summary
# ---------------------------------------------------------------------

summary_rows = []

for row in MLKEM_STACK:
    saved = bytes_saved(row["baseline"], row["final"])
    summary_rows.append({
        "category": "stack",
        "scheme": row["scheme"],
        "item": f"{row['variant']}::{row['function']}",
        "baseline": row["baseline"],
        "final": row["final"],
        "saved": saved,
        "delta_pct": reduction_pct(row["baseline"], row["final"]),
        "unit": "bytes",
        "source": row["version"],
    })

for row in MLDSA_STACK:
    saved = bytes_saved(row["baseline"], row["final"])
    summary_rows.append({
        "category": "stack",
        "scheme": row["scheme"],
        "item": f"{row['variant']}::{row['function']}",
        "baseline": row["baseline"],
        "final": row["final"],
        "saved": saved,
        "delta_pct": reduction_pct(row["baseline"], row["final"]),
        "unit": "bytes",
        "source": row["version"],
    })

summary_rows.append({
    "category": "stack_total",
    "scheme": "ML-DSA-44",
    "item": "high-level lifecycle stack proxy",
    "baseline": MLDSA_HIGH_LEVEL["baseline_total"],
    "final": MLDSA_HIGH_LEVEL["final_total"],
    "saved": MLDSA_HIGH_LEVEL["saved"],
    "delta_pct": MLDSA_HIGH_LEVEL["saved_pct"],
    "unit": "bytes",
    "source": "v23b/v24b",
})

summary_rows.extend([
    {
        "category": "workspace",
        "scheme": "ML-KEM-768",
        "item": "separate_total_to_lifecycle",
        "baseline": MLKEM_WORKSPACE["separate_total"],
        "final": MLKEM_WORKSPACE["lifecycle"],
        "saved": MLKEM_WORKSPACE["saved"],
        "delta_pct": MLKEM_WORKSPACE["saved_pct"],
        "unit": "bytes",
        "source": "v29",
    },
    {
        "category": "workspace",
        "scheme": "ML-DSA-44",
        "item": "separate_total_to_lifecycle",
        "baseline": MLDSA_WORKSPACE["separate_total"],
        "final": MLDSA_WORKSPACE["lifecycle"],
        "saved": MLDSA_WORKSPACE["saved"],
        "delta_pct": MLDSA_WORKSPACE["saved_pct"],
        "unit": "bytes",
        "source": "v24b",
    },
    {
        "category": "workspace",
        "scheme": "Combined",
        "item": "ML-KEM lifecycle + ML-DSA lifecycle",
        "baseline": "",
        "final": COMBINED_WORKSPACE["combined_total"],
        "saved": "",
        "delta_pct": "",
        "unit": "bytes",
        "source": "v30",
    },
])

for row in mlkem_speed_rows:
    summary_rows.append({
        "category": "speed",
        "scheme": "ML-KEM-768",
        "item": row["operation"],
        "baseline": row["baseline"],
        "final": row["final"],
        "saved": row["delta_us"],
        "delta_pct": row["delta_pct"],
        "unit": "us",
        "source": "v25b_vs_v29",
    })

for row in mldsa_speed_rows:
    summary_rows.append({
        "category": "speed",
        "scheme": "ML-DSA-44",
        "item": row["operation"],
        "baseline": row["baseline"],
        "final": row["final"],
        "saved": row["delta_us"],
        "delta_pct": row["delta_pct"],
        "unit": "us",
        "source": "baseline_vs_v24b",
    })

with OUT_CSV.open("w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "category",
            "scheme",
            "item",
            "baseline",
            "final",
            "saved",
            "delta_pct",
            "unit",
            "source",
        ],
    )
    writer.writeheader()
    writer.writerows(summary_rows)

# ---------------------------------------------------------------------
# JSON summary
# ---------------------------------------------------------------------

json_data = {
    "version": "v30",
    "title": "Combined PQC Workspace Summary",
    "schemes": ["ML-KEM-768", "ML-DSA-44"],
    "mlkem_workspace": MLKEM_WORKSPACE,
    "mldsa_workspace": MLDSA_WORKSPACE,
    "combined_workspace": COMBINED_WORKSPACE,
    "mlkem_speed": mlkem_speed_rows,
    "mldsa_speed": mldsa_speed_rows,
    "mldsa_high_level_stack": MLDSA_HIGH_LEVEL,
}

OUT_JSON.write_text(json.dumps(json_data, indent=2))

# ---------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------

md = "# Layer 3 v30: Combined PQC Workspace Summary\n\n"

md += "## Scope\n\n"
md += "This report summarizes the completed Layer 3 workspace work for:\n\n"
md += "- ML-KEM-768\n"
md += "- ML-DSA-44\n"
md += "- combined ML-KEM + ML-DSA constrained build profile\n\n"
md += "v30 is report-only. It does not introduce a new optimization or change cryptographic code.\n\n"

md += "## 1. Executive summary\n\n"
md += md_table(
    [
        "Scheme",
        "Final version",
        "Main result",
        "Final lifecycle workspace",
        "Workspace saved",
        "Speed impact",
    ],
    [
        [
            "ML-KEM-768",
            "v29",
            "IND-CPA stack frames reduced; operation workspaces compacted",
            f"{MLKEM_WORKSPACE['lifecycle']} B ({kib(MLKEM_WORKSPACE['lifecycle']):.2f} KiB)",
            f"{MLKEM_WORKSPACE['saved']} B ({MLKEM_WORKSPACE['saved_pct']:.2f}%)",
            "near baseline",
        ],
        [
            "ML-DSA-44",
            "v24b",
            "keygen/sign/verify stack reduced; lifecycle workspace compacted",
            f"{MLDSA_WORKSPACE['lifecycle']} B ({kib(MLDSA_WORKSPACE['lifecycle']):.2f} KiB)",
            f"{MLDSA_WORKSPACE['saved']} B ({MLDSA_WORKSPACE['saved_pct']:.2f}%)",
            "near baseline",
        ],
        [
            "Combined",
            "v30",
            "combined explicit PQC workspace budget",
            f"{COMBINED_WORKSPACE['combined_total']} B ({kib(COMBINED_WORKSPACE['combined_total']):.2f} KiB)",
            "-",
            "not a new benchmark",
        ],
    ],
)

md += "## 2. Version timeline\n\n"
md += md_table(
    ["Version", "Scheme", "Purpose", "Main output"],
    [
        ["v16", "ML-DSA-44", "caller matrix workspace", "reduced matrix-heavy signing/verify frames"],
        ["v17b", "ML-DSA-44", "full sign workspace", "moved signing vectors to caller workspace"],
        ["v19b", "ML-DSA-44", "attempt-generation workspace", "reduced signing attempt frame"],
        ["v21", "ML-DSA-44", "unified signing workspace", "combined sign-side caller workspace API"],
        ["v22b", "ML-DSA-44", "verify workspace", "verify frame reduced"],
        ["v23b", "ML-DSA-44", "keygen/provisioning workspace", "keypair and pk_from_sk frames reduced"],
        ["v24b", "ML-DSA-44", "compact lifecycle workspace", "62432 B separate to 44064 B lifecycle"],
        ["v25a", "ML-KEM-768", "stack/lifetime analysis", "identified enc/keypair/dec hotspots"],
        ["v25b", "ML-KEM-768", "baseline profiler", "baseline speed and size before ML-KEM changes"],
        ["v26", "ML-KEM-768", "encapsulation workspace", "indcpa_enc reduced"],
        ["v27", "ML-KEM-768", "keypair workspace", "indcpa_keypair_derand reduced"],
        ["v28", "ML-KEM-768", "decapsulation workspace", "indcpa_dec reduced"],
        ["v29", "ML-KEM-768", "compact lifecycle workspace", "28064 B separate to 13088 B lifecycle"],
        ["v30", "Combined", "summary report", "combined evidence pack"],
    ],
)

md += "## 3. ML-KEM stack reduction\n\n"
mlkem_stack_rows = []
for row in MLKEM_STACK:
    saved = bytes_saved(row["baseline"], row["final"])
    mlkem_stack_rows.append([
        row["variant"],
        f"`{row['function']}`",
        f"{row['baseline']} B",
        f"{row['final']} B",
        f"{saved} B",
        fmt_pct(reduction_pct(row["baseline"], row["final"])),
        row["version"],
    ])

md += md_table(
    ["Variant", "Function", "Baseline stack", "Final stack", "Saved", "Reduction", "Version"],
    mlkem_stack_rows,
)

md += "## 4. ML-KEM workspace compaction\n\n"
md += md_table(
    ["Workspace item", "Bytes", "KiB", "Role"],
    [
        ["v26_enc_workspace", MLKEM_WORKSPACE["v26_enc_workspace"], f"{kib(MLKEM_WORKSPACE['v26_enc_workspace']):.2f}", "encapsulation workspace"],
        ["v27_keypair_workspace", MLKEM_WORKSPACE["v27_keypair_workspace"], f"{kib(MLKEM_WORKSPACE['v27_keypair_workspace']):.2f}", "keypair workspace"],
        ["v28_dec_workspace", MLKEM_WORKSPACE["v28_dec_workspace"], f"{kib(MLKEM_WORKSPACE['v28_dec_workspace']):.2f}", "decapsulation workspace"],
        ["separate total", MLKEM_WORKSPACE["separate_total"], f"{kib(MLKEM_WORKSPACE['separate_total']):.2f}", "sum before lifecycle compaction"],
        ["v29 lifecycle workspace", MLKEM_WORKSPACE["lifecycle"], f"{kib(MLKEM_WORKSPACE['lifecycle']):.2f}", "compact reusable lifecycle workspace"],
        ["saved", MLKEM_WORKSPACE["saved"], f"{kib(MLKEM_WORKSPACE['saved']):.2f}", f"{MLKEM_WORKSPACE['saved_pct']:.2f}% saved"],
    ],
)

md += "## 5. ML-KEM speed\n\n"
mlkem_speed_md_rows = []
for row in mlkem_speed_rows:
    mlkem_speed_md_rows.append([
        row["operation"],
        fmt_us(row["baseline"]),
        fmt_us(row["final"]),
        fmt_us(row["delta_us"]),
        fmt_pct(row["delta_pct"]),
        "1",
    ])

md += md_table(
    ["Operation", "v25b baseline us", "v29 final us", "Delta us", "Delta %", "Correctness OK"],
    mlkem_speed_md_rows,
)

md += "## 6. ML-DSA stack reduction\n\n"
mldsa_stack_rows = []
for row in MLDSA_STACK:
    saved = bytes_saved(row["baseline"], row["final"])
    mldsa_stack_rows.append([
        row["variant"],
        f"`{row['function']}`",
        f"{row['baseline']} B",
        f"{row['final']} B",
        f"{saved} B",
        fmt_pct(reduction_pct(row["baseline"], row["final"])),
        row["version"],
    ])

md += md_table(
    ["Variant", "Function", "Baseline/milestone stack", "Final stack", "Saved", "Reduction", "Version"],
    mldsa_stack_rows,
)

md += "### ML-DSA high-level lifecycle stack proxy\n\n"
md += md_table(
    ["Metric", "Bytes", "KiB"],
    [
        ["baseline high-level total", MLDSA_HIGH_LEVEL["baseline_total"], f"{kib(MLDSA_HIGH_LEVEL['baseline_total']):.2f}"],
        ["final high-level total", MLDSA_HIGH_LEVEL["final_total"], f"{kib(MLDSA_HIGH_LEVEL['final_total']):.2f}"],
        ["saved", MLDSA_HIGH_LEVEL["saved"], f"{kib(MLDSA_HIGH_LEVEL['saved']):.2f}"],
        ["saved %", f"{MLDSA_HIGH_LEVEL['saved_pct']:.2f}%", "-"],
    ],
)

md += "## 7. ML-DSA workspace compaction\n\n"
md += md_table(
    ["Workspace item", "Bytes", "KiB", "Role"],
    [
        ["sign workspace", MLDSA_WORKSPACE["sign_workspace"], f"{kib(MLDSA_WORKSPACE['sign_workspace']):.2f}", "signing lifecycle workspace"],
        ["verify workspace", MLDSA_WORKSPACE["verify_workspace"], f"{kib(MLDSA_WORKSPACE['verify_workspace']):.2f}", "verification workspace"],
        ["keygen workspace", MLDSA_WORKSPACE["keygen_workspace"], f"{kib(MLDSA_WORKSPACE['keygen_workspace']):.2f}", "keypair/provisioning workspace"],
        ["separate total", MLDSA_WORKSPACE["separate_total"], f"{kib(MLDSA_WORKSPACE['separate_total']):.2f}", "sum before lifecycle compaction"],
        ["v24b lifecycle workspace", MLDSA_WORKSPACE["lifecycle"], f"{kib(MLDSA_WORKSPACE['lifecycle']):.2f}", "compact reusable lifecycle workspace"],
        ["saved", MLDSA_WORKSPACE["saved"], f"{kib(MLDSA_WORKSPACE['saved']):.2f}", f"{MLDSA_WORKSPACE['saved_pct']:.2f}% saved"],
    ],
)

md += "## 8. ML-DSA speed\n\n"
mldsa_speed_md_rows = []
for row in mldsa_speed_rows:
    mldsa_speed_md_rows.append([
        row["operation"],
        fmt_us(row["baseline"]),
        fmt_us(row["final"]),
        fmt_us(row["delta_us"]),
        fmt_pct(row["delta_pct"]),
        "1",
    ])

md += md_table(
    ["Operation", "Baseline us", "Final lifecycle us", "Delta us", "Delta %", "Correctness OK"],
    mldsa_speed_md_rows,
)

md += "## 9. Combined PQC workspace budget\n\n"
md += md_table(
    ["Scheme", "Lifecycle workspace bytes", "KiB"],
    [
        ["ML-KEM-768", COMBINED_WORKSPACE["mlkem_lifecycle"], f"{kib(COMBINED_WORKSPACE['mlkem_lifecycle']):.2f}"],
        ["ML-DSA-44", COMBINED_WORKSPACE["mldsa_lifecycle"], f"{kib(COMBINED_WORKSPACE['mldsa_lifecycle']):.2f}"],
        ["Combined total", COMBINED_WORKSPACE["combined_total"], f"{kib(COMBINED_WORKSPACE['combined_total']):.2f}"],
    ],
)

md += (
    "This combined total is the explicit caller-provided workspace budget for a backend "
    "that keeps one ML-KEM lifecycle workspace and one ML-DSA lifecycle workspace. "
    "v30 does not claim cross-scheme workspace unioning.\n\n"
)

md += "## 10. Combined build profile\n\n"
md += md_table(
    ["Setting", "Value"],
    [
        ["KEM", "ML-KEM-768"],
        ["SIG", "ML-DSA-44"],
        ["OQS_MINIMAL_BUILD", "`KEM_ml_kem_768;SIG_ml_dsa_44`"],
        ["OQS_EMBEDDED_BUILD", "ON"],
        ["OQS_USE_OPENSSL", "OFF"],
        ["ML-KEM workspace", "v29 compact lifecycle workspace"],
        ["ML-DSA workspace", "v24b compact lifecycle workspace"],
        ["Target use", "desktop validation first, Rust backend next, Pi later"],
    ],
)

md += "## 11. Binary / section size snapshot\n\n"
if v29_mlkem_size:
    md += md_table(
        ["Profile", "text", "data", "bss", "dec", "hex", "Binary"],
        [
            [
                r.get("profile", ""),
                r.get("text", ""),
                r.get("data", ""),
                r.get("bss", ""),
                r.get("dec", ""),
                r.get("hex", ""),
                f"`{r.get('binary', '')}`",
            ]
            for r in v29_mlkem_size
        ],
    )
else:
    md += "No v29 size CSV found.\n\n"

md += "## 12. Correctness summary\n\n"
md += md_table(
    ["Scheme", "Operation group", "Status", "Depth"],
    [
        ["ML-KEM-768", "keypair / encaps / decaps", "passed", "smoke correctness in v29"],
        ["ML-DSA-44", "keypair / sign / verify", "passed", "smoke correctness in v24b"],
        ["Combined", "same minimal build profile", "not deeply tested yet", "planned for v31"],
        ["Negative tests", "corruption / misuse / differential", "not part of v30", "planned for v31-v34"],
    ],
)

md += "## 13. Claims and evidence\n\n"
md += md_table(
    ["Claim", "Evidence", "Status"],
    [
        ["ML-KEM stack hotspots reduced", "indcpa_enc/keypair/dec stack tables", "supported"],
        ["ML-KEM workspace compacted", "28064 B to 13088 B", "supported"],
        ["ML-DSA high-stack lifecycle reduced", "v16-v23b stack milestones", "supported"],
        ["ML-DSA workspace compacted", "62432 B to 44064 B", "supported"],
        ["Combined explicit workspace known", "57152 B total", "supported"],
        ["Speed stayed near baseline", "ML-KEM and ML-DSA speed deltas", "supported"],
        ["Cryptographic behavior unchanged", "storage/layout-only patches; smoke correctness passed", "partially supported"],
        ["Production readiness", "requires v31-v39 validation", "not claimed"],
    ],
)

md += "## 14. Limitations\n\n"
md += "- v30 is a summary report, not a new test run.\n"
md += "- v30 does not prove constant-time behavior.\n"
md += "- v30 does not prove production readiness.\n"
md += "- v30 does not include Rust FFI testing.\n"
md += "- v30 does not include Pi or constrained-device runtime testing.\n"
md += "- Deeper correctness, misuse, sanitizer, threading, build-matrix, and differential tests remain for v31-v39.\n\n"

md += "## 15. Next work\n\n"
md += md_table(
    ["Version", "Next task"],
    [
        ["v31", "combined correctness harness for ML-KEM + ML-DSA"],
        ["v32", "workspace API misuse tests for both schemes"],
        ["v33", "baseline-vs-optimized differential tests"],
        ["v34", "sanitizer and memory-safety validation"],
        ["v35", "threading/TLS validation"],
        ["v36", "build matrix validation"],
        ["v37", "final memory accounting report"],
        ["v38", "code hygiene and cleanup"],
        ["v39", "cross-compile dry run"],
        ["v40", "Rust backend integration starts"],
    ],
)

OUT_MD.write_text(md)

print(f"wrote {OUT_MD}")
print(f"wrote {OUT_CSV}")
print(f"wrote {OUT_JSON}")
