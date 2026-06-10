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

START_MARKER = "/*\n * Layer 3 v15 experiment:"
END_MARKER = "static void mld_sample_s1_s2"


def v16_block(prefix: str) -> str:
    return f'''/*
 * Layer 3 v16 experiment:
 *
 * Caller-provided matrix workspace prototype.
 *
 * v15 moved mld_polymat into hidden static/BSS memory.
 * v16 makes the workspace explicit: the caller/profiler/device provides
 * the memory and this file only stores a thread-local pointer to it.
 *
 * This keeps the eager matrix path while reducing stack pressure.
 */
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_MATRIX_WORKSPACE)
typedef struct {{
  MLD_ALIGN mld_polymat mat;
}} mld_v16_matrix_workspace;

static _Thread_local mld_v16_matrix_workspace *mld_v16_tls_workspace;

size_t {prefix}_v16_matrix_workspace_bytes(void) {{
  return sizeof(mld_v16_matrix_workspace);
}}

int {prefix}_v16_matrix_workspace_set(void *workspace, size_t workspace_bytes) {{
  if (workspace == 0) {{
    mld_v16_tls_workspace = 0;
    return 0;
  }}

  if (workspace_bytes < sizeof(mld_v16_matrix_workspace)) {{
    return -1;
  }}

  mld_v16_tls_workspace = (mld_v16_matrix_workspace *)workspace;
  return 0;
}}

#define MLD_V16_ALLOC_MAT(name) \\
  mld_polymat *name = &mld_v16_tls_workspace->mat

#define MLD_V16_FREE_MAT(name) \\
  do {{ (void)(name); }} while (0)

#elif defined(MLD_CONFIG_EXPERIMENTAL_STATIC_MATRIX_WORKSPACE)
static MLD_ALIGN mld_polymat mld_v15_static_mat;

#define MLD_V16_ALLOC_MAT(name) \\
  mld_polymat *name = &mld_v15_static_mat

#define MLD_V16_FREE_MAT(name) \\
  do {{ (void)(name); }} while (0)

#else
#define MLD_V16_ALLOC_MAT(name) \\
  MLD_ALLOC(name, mld_polymat, 1, context)

#define MLD_V16_FREE_MAT(name) \\
  MLD_FREE(name, mld_polymat, 1, context)
#endif

'''


for path, prefix in TARGETS:
    text = path.read_text()

    start = text.find(START_MARKER)
    end = text.find(END_MARKER)

    if start == -1:
        raise SystemExit(f"v15 block start not found in {path}")

    if end == -1:
        raise SystemExit(f"end marker not found in {path}")

    text = text[:start] + v16_block(prefix) + text[end:]

    text = text.replace("MLD_V15_ALLOC_MAT", "MLD_V16_ALLOC_MAT")
    text = text.replace("MLD_V15_FREE_MAT", "MLD_V16_FREE_MAT")

    path.write_text(text)
    print(f"patched {path}")
