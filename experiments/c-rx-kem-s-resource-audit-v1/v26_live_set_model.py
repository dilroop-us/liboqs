#!/usr/bin/env python3

from pathlib import Path
import csv

ROOT = Path.home() / "pqc" / "liboqs"

RESULTS = (
    ROOT
    / "research-results"
    / "c-rx-kem-s-resource-audit-v1"
)

OUT = RESULTS / "v26_semantic_live_set.csv"

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

phases = [
    (
        "unpack_pk_and_frommsg",
        ["pkpv", "seed", "k"]
    ),

    (
        "gen_matrix",
        ["pkpv", "seed", "k", "at"]
    ),

    (
        "after_noise_generation",
        ["at", "sp", "pkpv", "ep", "k", "epp"]
    ),

    (
        "after_sp_cache",
        ["at", "sp", "pkpv", "ep", "sp_cache", "k", "epp"]
    ),

    (
        "during_matvec",
        ["at", "sp", "pkpv", "ep", "b",
         "sp_cache", "k", "epp"]
    ),

    (
        "during_basemul",
        ["sp", "pkpv", "ep", "b",
         "sp_cache", "v", "k", "epp"]
    ),

    (
        "after_basemul",
        ["ep", "b", "v", "k", "epp"]
    ),

    (
        "after_add_ep",
        ["b", "v", "k", "epp"]
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

allocated = 13088

print("v26 current semantic live-set model")
print()

for row in rows:
    print(
        f"{row['phase']:28s} "
        f"{row['semantic_live_bytes']:6d} B  "
        f"{row['live_objects']}"
    )

print()
print(
    f"semantic peak:   "
    f"{peak['semantic_live_bytes']} B"
)

print(
    f"peak phase:      "
    f"{peak['phase']}"
)

print(
    f"allocated v26:   "
    f"{allocated} B"
)

print(
    f"allocation gap:  "
    f"{allocated - peak['semantic_live_bytes']} B"
)

print()
print(f"wrote {OUT}")
