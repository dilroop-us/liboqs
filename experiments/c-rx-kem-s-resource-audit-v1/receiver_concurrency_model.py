#!/usr/bin/env python3

from pathlib import Path
import csv

ROOT = Path.home() / "pqc" / "liboqs"

RESULTS = (
    ROOT
    / "research-results"
    / "c-rx-kem-s-resource-audit-v1"
)

OUT = RESULTS / "receiver_concurrency_model.csv"

workspace_current = 13088

# Analytical S1 hypothesis from delayed generation.
workspace_s1_candidate = 9984

ciphertext = 1088
shared_secret = 32

# Known top-level frame only.
# Nested stack still excluded.
top_stack = 1376

shared_secret_key = 2400

current_per_active = (
    workspace_current
    + ciphertext
    + shared_secret
    + top_stack
)

s1_per_active = (
    workspace_s1_candidate
    + ciphertext
    + shared_secret
    + top_stack
)

rows = []

for incoming in [1, 2, 4, 8, 16, 32]:

    unbounded_current = (
        shared_secret_key
        + incoming * current_per_active
    )

    for pool in [1, 2, 4]:

        active = min(incoming, pool)
        queued = max(0, incoming - pool)

        bounded_current = (
            shared_secret_key
            + active * current_per_active
        )

        bounded_s1 = (
            shared_secret_key
            + active * s1_per_active
        )

        rows.append({
            "incoming": incoming,
            "pool": pool,
            "active": active,
            "queued": queued,
            "unbounded_current_bytes":
                unbounded_current,
            "bounded_current_bytes":
                bounded_current,
            "bounded_s1_hypothesis_bytes":
                bounded_s1,
            "s3_saving_vs_unbounded":
                unbounded_current - bounded_current,
            "additional_s1_saving":
                bounded_current - bounded_s1,
        })

with OUT.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=rows[0].keys()
    )

    writer.writeheader()
    writer.writerows(rows)

for row in rows:
    print(
        f"incoming={row['incoming']:2d} "
        f"pool={row['pool']} "
        f"active={row['active']} "
        f"queued={row['queued']:2d} "
        f"current={row['bounded_current_bytes']:7d} B "
        f"S1hyp={row['bounded_s1_hypothesis_bytes']:7d} B "
        f"S3save={row['s3_saving_vs_unbounded']:7d} B"
    )

print()
print(f"wrote {OUT}")
