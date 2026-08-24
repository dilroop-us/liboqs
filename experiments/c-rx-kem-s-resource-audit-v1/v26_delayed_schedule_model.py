#!/usr/bin/env python3

from pathlib import Path
import csv

ROOT = Path.home() / "pqc" / "liboqs"

RESULTS = (
    ROOT
    / "research-results"
    / "c-rx-kem-s-resource-audit-v1"
)

OUT = RESULTS / "v26_delayed_schedule_model.csv"

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
# RESEARCH HYPOTHESIS ONLY.
#
# Delay generation of:
#
#   ep
#   epp
#   k
#
# until after sp/pkpv/sp_cache are no longer required.
#
# No implementation has been changed.
#

phases = [
    (
        "unpack_pk",
        ["pkpv", "seed"]
    ),

    (
        "gen_matrix",
        ["pkpv", "seed", "at"]
    ),

    (
        "generate_sp",
        ["pkpv", "at", "sp"]
    ),

    (
        "compute_sp_cache",
        ["pkpv", "at", "sp", "sp_cache"]
    ),

    (
        "during_matvec",
        ["pkpv", "at", "sp", "sp_cache", "b"]
    ),

    (
        "during_basemul",
        ["pkpv", "sp", "sp_cache", "b", "v"]
    ),

    (
        "delayed_ep_epp_k_generation",
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

with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "phase",
            "live_objects",
            "semantic_live_bytes",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)

peak = max(
    rows,
    key=lambda x: x["semantic_live_bytes"]
)

current_allocated = 13088

candidate = peak["semantic_live_bytes"]

saving = current_allocated - candidate
saving_pct = saving / current_allocated * 100.0

print("C-RX-KEM-S1 delayed-generation model")
print()
print("NOTE: analytical hypothesis only; not implemented.")
print()

for row in rows:
    print(
        f"{row['phase']:32s} "
        f"{row['semantic_live_bytes']:6d} B  "
        f"{row['live_objects']}"
    )

print()
print(f"current workspace:     {current_allocated:6d} B")
print(f"candidate live peak:   {candidate:6d} B")
print(f"potential reduction:   {saving:6d} B")
print(f"potential reduction:   {saving_pct:6.2f} %")

print()
print(f"wrote {OUT}")
