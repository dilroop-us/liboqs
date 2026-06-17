#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"

TARGETS = [
    (
        ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c",
        "PQCP_MLDSA_NATIVE_MLDSA44_X86_64",
    ),
    (
        ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c",
        "PQCP_MLDSA_NATIVE_MLDSA44_C",
    ),
]

MARKER = "#endif /* MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE */\n\n"


def v21_block(prefix: str) -> str:
    return f"""
#if defined(MLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE) && \\
    defined(MLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE) && \\
    defined(MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE)

/*
 * v21 unified workspace API.
 *
 * This does not introduce a new buffer optimization.
 * It combines the v17b outer signing workspace and the v19b
 * attempt-generation workspace into one caller-provided block.
 */
#define MLD_V21_WORKSPACE_ALIGN ((size_t)64)

static size_t mld_v21_align_up(size_t value, size_t align) {{
  return (value + align - 1u) & ~(align - 1u);
}}

size_t {prefix}_v21_sign_workspace_bytes(void) {{
  const size_t sign_bytes = sizeof(mld_v17b_sign_workspace);
  const size_t sign_aligned = mld_v21_align_up(sign_bytes, MLD_V21_WORKSPACE_ALIGN);
  const size_t attempt_bytes = sizeof(mld_v19b_attempt_workspace);

  return sign_aligned + attempt_bytes;
}}

int {prefix}_v21_sign_workspace_set(void *workspace, size_t workspace_bytes) {{
  const size_t sign_bytes = sizeof(mld_v17b_sign_workspace);
  const size_t sign_aligned = mld_v21_align_up(sign_bytes, MLD_V21_WORKSPACE_ALIGN);
  const size_t total_bytes = {prefix}_v21_sign_workspace_bytes();
  uintptr_t base;
  uintptr_t attempt_base;

  if (workspace == 0 || workspace_bytes < total_bytes) {{
    return -1;
  }}

  base = (uintptr_t)workspace;

  if ((base & (uintptr_t)(MLD_V21_WORKSPACE_ALIGN - 1u)) != 0u) {{
    return -2;
  }}

  attempt_base = base + sign_aligned;

  mld_v17b_tls_workspace = (mld_v17b_sign_workspace *)base;
  mld_v19b_tls_attempt_workspace = (mld_v19b_attempt_workspace *)attempt_base;

  return 0;
}}

#endif /* MLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE */

"""


for path, prefix in TARGETS:
    text = path.read_text()

    backup = path.with_suffix(path.suffix + ".before_v21")
    if not backup.exists():
        backup.write_text(text)

    if f"{prefix}_v21_sign_workspace_bytes" in text:
        print(f"already patched {path}")
        continue

    if MARKER not in text:
        raise SystemExit(f"cannot find v19b marker in {path}")

    text = text.replace(MARKER, MARKER + v21_block(prefix), 1)
    path.write_text(text)
    print(f"patched {path}")
