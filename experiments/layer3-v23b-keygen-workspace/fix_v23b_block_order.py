#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"

TARGETS = [
    ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c",
    ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c",
]

START_MARKER = """#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE)

/*
 * v23b caller-provided keygen/provisioning workspace.
"""

END_MARKER = "#endif /* MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE */"

INSERT_BEFORE = "int mld_sign_keypair_internal("

for path in TARGETS:
    text = path.read_text()

    start = text.find(START_MARKER)
    if start == -1:
        raise SystemExit(f"cannot find v23b workspace block start in {path}")

    end = text.find(END_MARKER, start)
    if end == -1:
        raise SystemExit(f"cannot find v23b workspace block end in {path}")

    end = end + len(END_MARKER)

    # Preserve following blank lines if present.
    while end < len(text) and text[end] in "\n":
        end += 1

    block = text[start:end]
    text_without_block = text[:start] + text[end:]

    insert_at = text_without_block.find(INSERT_BEFORE)
    if insert_at == -1:
        raise SystemExit(f"cannot find keypair function in {path}")

    # Insert before keypair_internal so macros/types exist before first use.
    fixed = text_without_block[:insert_at] + block + "\n" + text_without_block[insert_at:]

    path.write_text(fixed)
    print(f"moved v23b block before keypair_internal in {path}")
