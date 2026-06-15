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

INSERT_BEFORE = """MLD_MUST_CHECK_RETURN_VALUE
static int mld_attempt_signature_generation"""

OLD_ALLOC_BLOCK = """  typedef union
  {
    mld_polyveck w1;
    mld_polyvecl tmp;
  } w1tmp_u;
  mld_polyveck *w1;
  mld_polyvecl *tmp;

  MLD_ALLOC(challenge_bytes, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_ALLOC(y, mld_yvec, 1, context);
  MLD_ALLOC(z, mld_poly, 1, context);
  MLD_ALLOC(w1tmp, w1tmp_u, 1, context);
  MLD_ALLOC(w0, mld_polyveck, 1, context);
  MLD_ALLOC(cp, mld_poly, 1, context);
  MLD_ALLOC(t, mld_poly, 1, context);
"""

NEW_ALLOC_BLOCK = """#if !defined(MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE)
  typedef union
  {
    mld_polyveck w1;
    mld_polyvecl tmp;
  } w1tmp_u;
#endif
  mld_polyveck *w1;
  mld_polyvecl *tmp;

#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE)
  MLD_V19B_REQUIRE_ATTEMPT_WORKSPACE();
  uint8_t *challenge_bytes = mld_v19b_tls_attempt_workspace->challenge_bytes;
  mld_yvec *y = &mld_v19b_tls_attempt_workspace->y;
  mld_poly *z = &mld_v19b_tls_attempt_workspace->z;
  mld_v19b_w1tmp_u *w1tmp = &mld_v19b_tls_attempt_workspace->w1tmp;
  mld_polyveck *w0 = &mld_v19b_tls_attempt_workspace->w0;
  mld_poly *cp = &mld_v19b_tls_attempt_workspace->cp;
  mld_poly *t = &mld_v19b_tls_attempt_workspace->t;
#else
  MLD_ALLOC(challenge_bytes, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_ALLOC(y, mld_yvec, 1, context);
  MLD_ALLOC(z, mld_poly, 1, context);
  MLD_ALLOC(w1tmp, w1tmp_u, 1, context);
  MLD_ALLOC(w0, mld_polyveck, 1, context);
  MLD_ALLOC(cp, mld_poly, 1, context);
  MLD_ALLOC(t, mld_poly, 1, context);
#endif
"""

OLD_FREE_BLOCK = """  MLD_FREE(t, mld_poly, 1, context);
  MLD_FREE(cp, mld_poly, 1, context);
  MLD_FREE(w0, mld_polyveck, 1, context);
  MLD_FREE(w1tmp, w1tmp_u, 1, context);
  MLD_FREE(z, mld_poly, 1, context);
  MLD_FREE(y, mld_yvec, 1, context);
  MLD_FREE(challenge_bytes, uint8_t, MLDSA_CTILDEBYTES, context);
"""

NEW_FREE_BLOCK = """#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE)
  MLD_V19B_CLEAN_ATTEMPT_WORKSPACE();
#else
  MLD_FREE(t, mld_poly, 1, context);
  MLD_FREE(cp, mld_poly, 1, context);
  MLD_FREE(w0, mld_polyveck, 1, context);
  MLD_FREE(w1tmp, w1tmp_u, 1, context);
  MLD_FREE(z, mld_poly, 1, context);
  MLD_FREE(y, mld_yvec, 1, context);
  MLD_FREE(challenge_bytes, uint8_t, MLDSA_CTILDEBYTES, context);
#endif
"""


def v19b_block(prefix: str) -> str:
    return f"""
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE)

typedef union {{
  MLD_ALIGN mld_polyveck w1;
  MLD_ALIGN mld_polyvecl tmp;
}} mld_v19b_w1tmp_u;

typedef struct {{
  MLD_ALIGN mld_yvec y;
  MLD_ALIGN mld_v19b_w1tmp_u w1tmp;
  MLD_ALIGN mld_polyveck w0;
  MLD_ALIGN mld_poly z;
  MLD_ALIGN mld_poly cp;
  MLD_ALIGN mld_poly t;
  uint8_t challenge_bytes[MLDSA_CTILDEBYTES];
}} mld_v19b_attempt_workspace;

static _Thread_local mld_v19b_attempt_workspace *mld_v19b_tls_attempt_workspace;

size_t {prefix}_v19b_attempt_workspace_bytes(void) {{
  return sizeof(mld_v19b_attempt_workspace);
}}

int {prefix}_v19b_attempt_workspace_set(void *workspace, size_t workspace_bytes) {{
  if (workspace == 0 || workspace_bytes < sizeof(mld_v19b_attempt_workspace)) {{
    return -1;
  }}

  mld_v19b_tls_attempt_workspace = (mld_v19b_attempt_workspace *)workspace;
  return 0;
}}

#define MLD_V19B_REQUIRE_ATTEMPT_WORKSPACE() \\
  do {{ \\
    if (mld_v19b_tls_attempt_workspace == 0) {{ \\
      return MLD_ERR_OUT_OF_MEMORY; \\
    }} \\
  }} while (0)

#if defined(MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE)
static void mld_v19b_cleanse(void *ptr, size_t len) {{
  volatile uint8_t *p = (volatile uint8_t *)ptr;

  while (len > 0) {{
    *p++ = 0;
    len--;
  }}
}}

#define MLD_V19B_CLEAN_ATTEMPT_WORKSPACE() \\
  do {{ \\
    if (mld_v19b_tls_attempt_workspace != 0) {{ \\
      mld_v19b_cleanse(mld_v19b_tls_attempt_workspace, \\
                       sizeof(*mld_v19b_tls_attempt_workspace)); \\
    }} \\
  }} while (0)
#else
#define MLD_V19B_CLEAN_ATTEMPT_WORKSPACE() \\
  do {{ }} while (0)
#endif

#endif /* MLD_CONFIG_EXPERIMENTAL_CALLER_ATTEMPT_WORKSPACE */

"""


for path, prefix in TARGETS:
    text = path.read_text()

    backup = path.with_suffix(path.suffix + ".before_v19b")
    if not backup.exists():
        backup.write_text(text)

    if f"{prefix}_v19b_attempt_workspace_bytes" not in text:
        if INSERT_BEFORE not in text:
            raise SystemExit(f"cannot find v19b insert point in {path}")

        text = text.replace(INSERT_BEFORE, v19b_block(prefix) + INSERT_BEFORE, 1)

    if OLD_ALLOC_BLOCK not in text and NEW_ALLOC_BLOCK not in text:
        raise SystemExit(f"cannot find allocation block in {path}")

    if NEW_ALLOC_BLOCK not in text:
        text = text.replace(OLD_ALLOC_BLOCK, NEW_ALLOC_BLOCK, 1)

    if OLD_FREE_BLOCK not in text and NEW_FREE_BLOCK not in text:
        raise SystemExit(f"cannot find free block in {path}")

    if NEW_FREE_BLOCK not in text:
        text = text.replace(OLD_FREE_BLOCK, NEW_FREE_BLOCK, 1)

    path.write_text(text)
    print(f"patched {path}")
