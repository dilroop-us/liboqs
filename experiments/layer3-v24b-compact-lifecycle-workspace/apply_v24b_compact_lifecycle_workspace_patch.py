#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"

TARGETS = [
    (
        "x86_64",
        ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c",
        "PQCP_MLDSA_NATIVE_MLDSA44_X86_64",
    ),
    (
        "ref",
        ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c",
        "PQCP_MLDSA_NATIVE_MLDSA44_C",
    ),
]

INSERT_AFTER = "#endif /* MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE */"

V24_MARKER = "MLD_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE"


def make_block(prefix: str) -> str:
    template = r'''

#if defined(MLD_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE) && \
    defined(MLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE) && \
    defined(MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE) && \
    defined(MLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE) && \
    defined(MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE) && \
    defined(MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE)

/*
 * v24b compact lifecycle workspace.
 *
 * One caller-provided buffer is mapped into:
 *
 *   common matrix region
 *   operation-specific union region
 *
 * The older internal workspace APIs are reused:
 *
 *   v21 sign workspace     -> base
 *   v22b verify workspace  -> base + sizeof(mld_polymat)
 *   v23b keygen workspace  -> base + sizeof(mld_polymat)
 *
 * Safety condition:
 *   one workspace per thread/context; no concurrent sign/verify/keygen
 *   operation on the same workspace.
 */

#define MLD_V24_WORKSPACE_ALIGN ((size_t)64)

static size_t mld_v24_max_size(size_t a, size_t b) {
  return a > b ? a : b;
}

static size_t mld_v24_max_size3(size_t a, size_t b, size_t c) {
  return mld_v24_max_size(mld_v24_max_size(a, b), c);
}

size_t PREFIX_v24_lifecycle_workspace_bytes(void) {
  const size_t matrix_bytes = sizeof(mld_polymat);

  const size_t sign_bytes =
      PREFIX_v21_sign_workspace_bytes();

  const size_t verify_bytes =
      PREFIX_v22b_verify_workspace_bytes();

  const size_t keygen_bytes =
      PREFIX_v23b_keygen_workspace_bytes();

  const size_t sign_op_bytes =
      sign_bytes > matrix_bytes ? sign_bytes - matrix_bytes : 0u;

  const size_t op_union_bytes =
      mld_v24_max_size3(sign_op_bytes, verify_bytes, keygen_bytes);

  return matrix_bytes + op_union_bytes;
}

int PREFIX_v24_lifecycle_workspace_set(void *workspace,
                                       size_t workspace_bytes) {
  const size_t matrix_bytes = sizeof(mld_polymat);
  const size_t total_bytes =
      PREFIX_v24_lifecycle_workspace_bytes();

  const size_t op_union_bytes =
      total_bytes > matrix_bytes ? total_bytes - matrix_bytes : 0u;

  uintptr_t base;
  uintptr_t op_base;

  int rc;

  if (workspace == 0 || workspace_bytes < total_bytes) {
    return -1;
  }

  base = (uintptr_t)workspace;

  if ((base & (uintptr_t)(MLD_V24_WORKSPACE_ALIGN - 1u)) != 0u) {
    return -2;
  }

  op_base = base + matrix_bytes;

  /*
   * v21 uses the full compact buffer:
   *   matrix + sign operation region
   */
  rc = PREFIX_v21_sign_workspace_set(workspace, workspace_bytes);
  if (rc != 0) {
    return -3;
  }

  /*
   * v22b verify workspace overlays the operation-specific region.
   */
  rc = PREFIX_v22b_verify_workspace_set((void *)op_base, op_union_bytes);
  if (rc != 0) {
    return -4;
  }

  /*
   * v23b keygen/provisioning workspace also overlays the same
   * operation-specific region.
   */
  rc = PREFIX_v23b_keygen_workspace_set((void *)op_base, op_union_bytes);
  if (rc != 0) {
    return -5;
  }

  return 0;
}

#endif /* MLD_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE */
'''
    return template.replace("PREFIX", prefix)


for variant, path, prefix in TARGETS:
    text = path.read_text()

    if V24_MARKER in text:
        print(f"{variant}: v24b block already present, skipping {path}")
        continue

    marker_idx = text.find(INSERT_AFTER)

    if marker_idx == -1:
        raise SystemExit(f"{variant}: could not find insertion marker: {INSERT_AFTER}")

    insert_at = marker_idx + len(INSERT_AFTER)

    block = make_block(prefix)

    text = text[:insert_at] + block + text[insert_at:]

    path.write_text(text)

    print(f"{variant}: patched {path}")
