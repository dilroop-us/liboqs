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

START_MARKERS = [
    "/*\n * Layer 3 v16 experiment:",
    "/*\n * Layer 3 v17b experiment:",
]

END_MARKER = "static void mld_sample_s1_s2"


def v17b_block(prefix: str) -> str:
    return f'''/*
 * Layer 3 v17b experiment:
 *
 * Caller-provided full signing workspace prototype.
 *
 * v16 moved only mld_polymat out of stack into caller-owned memory.
 * v17b also moves the large signing secret-key NTT buffers:
 *
 *   - mld_sk_s1hat
 *   - mld_sk_s2hat
 *   - mld_sk_t0hat
 *
 * v17a showed these buffers overlap in lifetime, so simple union-based
 * reuse is not safe. Instead, v17b keeps separate buffers but moves them
 * into an explicit caller-provided workspace.
 */
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_SIGN_WORKSPACE)
typedef struct {{
  MLD_ALIGN mld_polymat mat;
  MLD_ALIGN mld_sk_s1hat s1hat;
  MLD_ALIGN mld_sk_s2hat s2hat;
  MLD_ALIGN mld_sk_t0hat t0hat;
}} mld_v17b_sign_workspace;

static _Thread_local mld_v17b_sign_workspace *mld_v17b_tls_workspace;

size_t {prefix}_v17b_sign_workspace_bytes(void) {{
  return sizeof(mld_v17b_sign_workspace);
}}

int {prefix}_v17b_sign_workspace_set(void *workspace, size_t workspace_bytes) {{
  if (workspace == 0) {{
    mld_v17b_tls_workspace = 0;
    return 0;
  }}

  if (workspace_bytes < sizeof(mld_v17b_sign_workspace)) {{
    return -1;
  }}

  mld_v17b_tls_workspace = (mld_v17b_sign_workspace *)workspace;
  return 0;
}}

#define MLD_V17B_REQUIRE_WORKSPACE() \\
  do {{ \\
    if (mld_v17b_tls_workspace == 0) {{ \\
      return -1; \\
    }} \\
  }} while (0)

#define MLD_V17B_ALLOC_MAT(name) \\
  MLD_V17B_REQUIRE_WORKSPACE(); \\
  mld_polymat *name = &mld_v17b_tls_workspace->mat

#define MLD_V17B_FREE_MAT(name) \\
  do {{ (void)(name); }} while (0)

#define MLD_V17B_ALLOC_S1HAT(name) \\
  MLD_V17B_REQUIRE_WORKSPACE(); \\
  mld_sk_s1hat *name = &mld_v17b_tls_workspace->s1hat

#define MLD_V17B_FREE_S1HAT(name) \\
  do {{ (void)(name); }} while (0)

#define MLD_V17B_ALLOC_S2HAT(name) \\
  MLD_V17B_REQUIRE_WORKSPACE(); \\
  mld_sk_s2hat *name = &mld_v17b_tls_workspace->s2hat

#define MLD_V17B_FREE_S2HAT(name) \\
  do {{ (void)(name); }} while (0)

#define MLD_V17B_ALLOC_T0HAT(name) \\
  MLD_V17B_REQUIRE_WORKSPACE(); \\
  mld_sk_t0hat *name = &mld_v17b_tls_workspace->t0hat

#define MLD_V17B_FREE_T0HAT(name) \\
  do {{ (void)(name); }} while (0)

#elif defined(MLD_CONFIG_EXPERIMENTAL_CALLER_MATRIX_WORKSPACE)
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

#define MLD_V17B_ALLOC_MAT(name) \\
  mld_polymat *name = &mld_v16_tls_workspace->mat

#define MLD_V17B_FREE_MAT(name) \\
  do {{ (void)(name); }} while (0)

#define MLD_V17B_ALLOC_S1HAT(name) \\
  MLD_ALLOC(name, mld_sk_s1hat, 1, context)

#define MLD_V17B_FREE_S1HAT(name) \\
  MLD_FREE(name, mld_sk_s1hat, 1, context)

#define MLD_V17B_ALLOC_S2HAT(name) \\
  MLD_ALLOC(name, mld_sk_s2hat, 1, context)

#define MLD_V17B_FREE_S2HAT(name) \\
  MLD_FREE(name, mld_sk_s2hat, 1, context)

#define MLD_V17B_ALLOC_T0HAT(name) \\
  MLD_ALLOC(name, mld_sk_t0hat, 1, context)

#define MLD_V17B_FREE_T0HAT(name) \\
  MLD_FREE(name, mld_sk_t0hat, 1, context)

#elif defined(MLD_CONFIG_EXPERIMENTAL_STATIC_MATRIX_WORKSPACE)
static MLD_ALIGN mld_polymat mld_v15_static_mat;

#define MLD_V17B_ALLOC_MAT(name) \\
  mld_polymat *name = &mld_v15_static_mat

#define MLD_V17B_FREE_MAT(name) \\
  do {{ (void)(name); }} while (0)

#define MLD_V17B_ALLOC_S1HAT(name) \\
  MLD_ALLOC(name, mld_sk_s1hat, 1, context)

#define MLD_V17B_FREE_S1HAT(name) \\
  MLD_FREE(name, mld_sk_s1hat, 1, context)

#define MLD_V17B_ALLOC_S2HAT(name) \\
  MLD_ALLOC(name, mld_sk_s2hat, 1, context)

#define MLD_V17B_FREE_S2HAT(name) \\
  MLD_FREE(name, mld_sk_s2hat, 1, context)

#define MLD_V17B_ALLOC_T0HAT(name) \\
  MLD_ALLOC(name, mld_sk_t0hat, 1, context)

#define MLD_V17B_FREE_T0HAT(name) \\
  MLD_FREE(name, mld_sk_t0hat, 1, context)

#else
#define MLD_V17B_ALLOC_MAT(name) \\
  MLD_ALLOC(name, mld_polymat, 1, context)

#define MLD_V17B_FREE_MAT(name) \\
  MLD_FREE(name, mld_polymat, 1, context)

#define MLD_V17B_ALLOC_S1HAT(name) \\
  MLD_ALLOC(name, mld_sk_s1hat, 1, context)

#define MLD_V17B_FREE_S1HAT(name) \\
  MLD_FREE(name, mld_sk_s1hat, 1, context)

#define MLD_V17B_ALLOC_S2HAT(name) \\
  MLD_ALLOC(name, mld_sk_s2hat, 1, context)

#define MLD_V17B_FREE_S2HAT(name) \\
  MLD_FREE(name, mld_sk_s2hat, 1, context)

#define MLD_V17B_ALLOC_T0HAT(name) \\
  MLD_ALLOC(name, mld_sk_t0hat, 1, context)

#define MLD_V17B_FREE_T0HAT(name) \\
  MLD_FREE(name, mld_sk_t0hat, 1, context)
#endif

'''


def find_start(text: str) -> int:
    positions = [text.find(marker) for marker in START_MARKERS]
    positions = [p for p in positions if p != -1]
    return min(positions) if positions else -1


for path, prefix in TARGETS:
    text = path.read_text()

    start = find_start(text)
    end = text.find(END_MARKER)

    if start == -1:
        raise SystemExit(f"workspace block start not found in {path}")

    if end == -1:
        raise SystemExit(f"end marker not found in {path}")

    text = text[:start] + v17b_block(prefix) + text[end:]

    replacements = {
        "MLD_V16_ALLOC_MAT": "MLD_V17B_ALLOC_MAT",
        "MLD_V16_FREE_MAT": "MLD_V17B_FREE_MAT",

        "MLD_ALLOC(s1hat, mld_sk_s1hat, 1, context);": "MLD_V17B_ALLOC_S1HAT(s1hat);",
        "MLD_FREE(s1hat, mld_sk_s1hat, 1, context);": "MLD_V17B_FREE_S1HAT(s1hat);",

        "MLD_ALLOC(s2hat, mld_sk_s2hat, 1, context);": "MLD_V17B_ALLOC_S2HAT(s2hat);",
        "MLD_FREE(s2hat, mld_sk_s2hat, 1, context);": "MLD_V17B_FREE_S2HAT(s2hat);",

        "MLD_ALLOC(t0hat, mld_sk_t0hat, 1, context);": "MLD_V17B_ALLOC_T0HAT(t0hat);",
        "MLD_FREE(t0hat, mld_sk_t0hat, 1, context);": "MLD_V17B_FREE_T0HAT(t0hat);",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    path.write_text(text)
    print(f"patched {path}")
