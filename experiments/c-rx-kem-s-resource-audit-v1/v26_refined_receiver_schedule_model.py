#!/usr/bin/env python3

from pathlib import Path
import csv

ROOT = Path.home() / "pqc" / "liboqs"

RESULTS = (
    ROOT
    / "research-results"
    / "c-rx-kem-s-resource-audit-v1"
)

OUT = RESULTS / "v26_refined_receiver_schedule_model.csv"

sizes = {
    "at": 4608,
    "sp": 1536,
    "pkpv": 1536,
    "ep": 1536,
    "b": 1536,
    "sp_cache": 768,
    "v": 512,
    "k": 512,
    "epp": 512,
    "seed": 32,
}

#
# Analytical C-RX-KEM-S1 receiver schedule.
#
# Hypotheses:
#
# 1. Extract matrix seed without immediately decoding pkpv.
# 2. Delay pkpv decode until after matrix-vector multiplication.
# 3. Delay ep/epp/k generation until after heavy multiply state dies.
#
# No cryptographic implementation is changed by this script.
#

phases = [
    (
        "extract_seed_only",
        ["seed"]
    ),

    (
        "generate_matrix",
        ["seed", "at"]
    ),

    (
        "generate_sp",
        ["at", "sp"]
    ),

    (
        "compute_sp_cache",
        ["at", "sp", "sp_cache"]
    ),

    (
        "matrix_vector_multiply",
        ["at", "sp", "sp_cache", "b"]
    ),

    (
        "late_decode_pkpv",
        ["sp", "sp_cache", "b", "pkpv"]
    ),

    (
        "basemul",
        ["sp", "sp_cache", "b", "pkpv", "v"]
    ),

    (
        "late_generate_ep_epp_k",
        ["b", "v", "ep", "epp", "k"]
    ),

    (
        "after_add_ep",
        ["b", "v", "epp", "k"]
    ),

    (
        "after_add_epp",
        ["b", "v", "k"]
    ),

    (
        "pack_ciphertext",
        ["b", "v"]
    ),
]

rows = []

for phase, objects in phases:
    total = sum(sizes[x] for x in objects)

    rows.append({
        "phase": phase,
        "live_objects": "+".join(objects),
        "semantic_live_bytes": total,
    })

peak = max(
    rows,
    key=lambda x: x["semantic_live_bytes"]
)

current = 13088
candidate = peak["semantic_live_bytes"]
saving = current - candidate

with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "phase",
            "live_objects",
            "semantic_live_bytes",
        ]
    )

    writer.writeheader()
    writer.writerows(rows)

print("C-RX-KEM-S1 refined receiver scheduling model")
print()
print("ANALYTICAL HYPOTHESIS ONLY")
print()

for row in rows:
    print(
        f"{row['phase']:30s} "
        f"{row['semantic_live_bytes']:6d} B  "
        f"{row['live_objects']}"
    )

print()
print(f"current v26 workspace:     {current:6d} B")
print(f"candidate semantic peak:   {candidate:6d} B")
print(f"potential saving:          {saving:6d} B")
print(f"peak phase:                {peak['phase']}")
print()
print(f"wrote {OUT}")
