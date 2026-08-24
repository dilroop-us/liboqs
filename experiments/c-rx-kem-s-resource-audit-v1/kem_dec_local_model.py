#!/usr/bin/env python3

from pathlib import Path

ROOT = Path.home() / "pqc" / "liboqs"

LOG = (
    ROOT
    / "research-results"
    / "c-rx-kem-s-resource-audit-v1"
    / "kem_resource_probe.log"
)

OUT = (
    ROOT
    / "research-results"
    / "c-rx-kem-s-resource-audit-v1"
    / "kem_dec_local_model.txt"
)

metrics = {}

for line in LOG.read_text().splitlines():
    parts = line.strip().split(",")

    if len(parts) == 3 and parts[0] == "AUDIT_METRIC":
        try:
            metrics[parts[1]] = int(parts[2])
        except ValueError:
            pass

symbytes = metrics["shared_secret_bytes"]
ciphertext = metrics["ciphertext_bytes"]

buf = 2 * symbytes
kr = 2 * symbytes
tmp = symbytes + ciphertext

explicit = buf + kr + tmp

measured_static_frame = 1376

lines = [
    "ML-KEM receiver outer-function local model",
    "",
    f"buf:                    {buf:6d} B",
    f"kr:                     {kr:6d} B",
    f"tmp:                    {tmp:6d} B",
    "--------------------------------",
    f"explicit arrays:        {explicit:6d} B",
    "",
    f"measured static frame:  {measured_static_frame:6d} B",
    f"other frame overhead:   {measured_static_frame-explicit:6d} B",
]

text = "\n".join(lines)

print(text)

OUT.write_text(text + "\n", encoding="utf-8")
