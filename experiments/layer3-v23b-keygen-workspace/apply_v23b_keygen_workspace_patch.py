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

V22B_MARKER = "#endif /* MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE */\n\n"

OLD_KEYPAIR_ALLOC = """  MLD_ALLOC(seedbuf, uint8_t, 2 * MLDSA_SEEDBYTES + MLDSA_CRHBYTES, context);
  MLD_ALLOC(inbuf, uint8_t, MLDSA_SEEDBYTES + 2, context);
  MLD_ALLOC(tr, uint8_t, MLDSA_TRBYTES, context);
  MLD_ALLOC(s1, mld_polyvecl, 1, context);
  MLD_ALLOC(s2, mld_polyveck, 1, context);
"""

NEW_KEYPAIR_ALLOC = """#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE)
  MLD_V23B_REQUIRE_KEYGEN_WORKSPACE();

  uint8_t *seedbuf = mld_v23b_tls_keygen_workspace->seedbuf;
  uint8_t *inbuf = mld_v23b_tls_keygen_workspace->inbuf;
  uint8_t *tr = mld_v23b_tls_keygen_workspace->tr;
  mld_polyvecl *s1 = &mld_v23b_tls_keygen_workspace->s1;
  mld_polyveck *s2 = &mld_v23b_tls_keygen_workspace->s2;
#else
  MLD_ALLOC(seedbuf, uint8_t, 2 * MLDSA_SEEDBYTES + MLDSA_CRHBYTES, context);
  MLD_ALLOC(inbuf, uint8_t, MLDSA_SEEDBYTES + 2, context);
  MLD_ALLOC(tr, uint8_t, MLDSA_TRBYTES, context);
  MLD_ALLOC(s1, mld_polyvecl, 1, context);
  MLD_ALLOC(s2, mld_polyveck, 1, context);
#endif
"""

OLD_KEYPAIR_CLEANUP = """cleanup:
  /* @[FIPS204, Section 3.6.3] Destruction of intermediate values. */
  MLD_FREE(s2, mld_polyveck, 1, context);
  MLD_FREE(s1, mld_polyvecl, 1, context);
  MLD_FREE(tr, uint8_t, MLDSA_TRBYTES, context);
  MLD_FREE(inbuf, uint8_t, MLDSA_SEEDBYTES + 2, context);
  MLD_FREE(seedbuf, uint8_t, 2 * MLDSA_SEEDBYTES + MLDSA_CRHBYTES, context);

  if (ret != 0)
"""

NEW_KEYPAIR_CLEANUP = """cleanup:
  /* @[FIPS204, Section 3.6.3] Destruction of intermediate values. */
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE)
  MLD_V23B_CLEAN_KEYGEN_WORKSPACE();
#else
  MLD_FREE(s2, mld_polyveck, 1, context);
  MLD_FREE(s1, mld_polyvecl, 1, context);
  MLD_FREE(tr, uint8_t, MLDSA_TRBYTES, context);
  MLD_FREE(inbuf, uint8_t, MLDSA_SEEDBYTES + 2, context);
  MLD_FREE(seedbuf, uint8_t, 2 * MLDSA_SEEDBYTES + MLDSA_CRHBYTES, context);
#endif

  if (ret != 0)
"""

OLD_PK_ALLOC = """  MLD_ALLOC(rho, uint8_t, MLDSA_SEEDBYTES, context);
  MLD_ALLOC(tr, uint8_t, MLDSA_TRBYTES, context);
  MLD_ALLOC(tr_computed, uint8_t, MLDSA_TRBYTES, context);
  MLD_ALLOC(key, uint8_t, MLDSA_SEEDBYTES, context);
  MLD_ALLOC(s1, mld_polyvecl, 1, context);
  MLD_ALLOC(s2, mld_polyveck, 1, context);
  MLD_ALLOC(t0_packed, uint8_t, MLDSA_K *MLDSA_POLYT0_PACKEDBYTES, context);
"""

NEW_PK_ALLOC = """#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE)
  MLD_V23B_REQUIRE_KEYGEN_WORKSPACE();

  uint8_t *rho = mld_v23b_tls_keygen_workspace->rho;
  uint8_t *tr = mld_v23b_tls_keygen_workspace->tr;
  uint8_t *tr_computed = mld_v23b_tls_keygen_workspace->tr_computed;
  uint8_t *key = mld_v23b_tls_keygen_workspace->key;
  mld_polyvecl *s1 = &mld_v23b_tls_keygen_workspace->s1;
  mld_polyveck *s2 = &mld_v23b_tls_keygen_workspace->s2;
  uint8_t *t0_packed = mld_v23b_tls_keygen_workspace->t0_packed;
#else
  MLD_ALLOC(rho, uint8_t, MLDSA_SEEDBYTES, context);
  MLD_ALLOC(tr, uint8_t, MLDSA_TRBYTES, context);
  MLD_ALLOC(tr_computed, uint8_t, MLDSA_TRBYTES, context);
  MLD_ALLOC(key, uint8_t, MLDSA_SEEDBYTES, context);
  MLD_ALLOC(s1, mld_polyvecl, 1, context);
  MLD_ALLOC(s2, mld_polyveck, 1, context);
  MLD_ALLOC(t0_packed, uint8_t, MLDSA_K *MLDSA_POLYT0_PACKEDBYTES, context);
#endif
"""

OLD_PK_CLEANUP = """  /* @[FIPS204, Section 3.6.3] Destruction of intermediate values. */
  MLD_FREE(t0_packed, uint8_t, MLDSA_K *MLDSA_POLYT0_PACKEDBYTES, context);
  MLD_FREE(s2, mld_polyveck, 1, context);
  MLD_FREE(s1, mld_polyvecl, 1, context);
  MLD_FREE(key, uint8_t, MLDSA_SEEDBYTES, context);
  MLD_FREE(tr_computed, uint8_t, MLDSA_TRBYTES, context);
  MLD_FREE(tr, uint8_t, MLDSA_TRBYTES, context);
  MLD_FREE(rho, uint8_t, MLDSA_SEEDBYTES, context);

  return ret;
"""

NEW_PK_CLEANUP = """  /* @[FIPS204, Section 3.6.3] Destruction of intermediate values. */
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE)
  MLD_V23B_CLEAN_KEYGEN_WORKSPACE();
#else
  MLD_FREE(t0_packed, uint8_t, MLDSA_K *MLDSA_POLYT0_PACKEDBYTES, context);
  MLD_FREE(s2, mld_polyveck, 1, context);
  MLD_FREE(s1, mld_polyvecl, 1, context);
  MLD_FREE(key, uint8_t, MLDSA_SEEDBYTES, context);
  MLD_FREE(tr_computed, uint8_t, MLDSA_TRBYTES, context);
  MLD_FREE(tr, uint8_t, MLDSA_TRBYTES, context);
  MLD_FREE(rho, uint8_t, MLDSA_SEEDBYTES, context);
#endif

  return ret;
"""


def v23b_block(prefix: str) -> str:
    return f"""
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE)

/*
 * v23b caller-provided keygen/provisioning workspace.
 *
 * v23a showed keypair_internal and pk_from_sk are local-buffer dominated.
 * v23b moves those buffers out of function stack and into explicit caller-owned
 * workspace.
 */
typedef struct {{
  MLD_ALIGN mld_polyvecl s1;
  MLD_ALIGN mld_polyveck s2;

  MLD_ALIGN uint8_t t0_packed[MLDSA_K * MLDSA_POLYT0_PACKEDBYTES];

  MLD_ALIGN uint8_t seedbuf[2 * MLDSA_SEEDBYTES + MLDSA_CRHBYTES];
  MLD_ALIGN uint8_t inbuf[MLDSA_SEEDBYTES + 2];

  MLD_ALIGN uint8_t tr[MLDSA_TRBYTES];
  MLD_ALIGN uint8_t tr_computed[MLDSA_TRBYTES];

  MLD_ALIGN uint8_t rho[MLDSA_SEEDBYTES];
  MLD_ALIGN uint8_t key[MLDSA_SEEDBYTES];
}} mld_v23b_keygen_workspace;

static _Thread_local mld_v23b_keygen_workspace *mld_v23b_tls_keygen_workspace;

size_t {prefix}_v23b_keygen_workspace_bytes(void) {{
  return sizeof(mld_v23b_keygen_workspace);
}}

int {prefix}_v23b_keygen_workspace_set(void *workspace, size_t workspace_bytes) {{
  if (workspace == 0 || workspace_bytes < sizeof(mld_v23b_keygen_workspace)) {{
    return -1;
  }}

  if ((((uintptr_t)workspace) & (uintptr_t)63u) != 0u) {{
    return -2;
  }}

  mld_v23b_tls_keygen_workspace = (mld_v23b_keygen_workspace *)workspace;
  return 0;
}}

#define MLD_V23B_REQUIRE_KEYGEN_WORKSPACE() \\
  do {{ \\
    if (mld_v23b_tls_keygen_workspace == 0) {{ \\
      return MLD_ERR_OUT_OF_MEMORY; \\
    }} \\
  }} while (0)

#if defined(MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE)
static void mld_v23b_cleanse(void *ptr, size_t len) {{
  volatile uint8_t *p = (volatile uint8_t *)ptr;

  while (len > 0) {{
    *p++ = 0;
    len--;
  }}
}}

#define MLD_V23B_CLEAN_KEYGEN_WORKSPACE() \\
  do {{ \\
    if (mld_v23b_tls_keygen_workspace != 0) {{ \\
      mld_v23b_cleanse(mld_v23b_tls_keygen_workspace, \\
                       sizeof(*mld_v23b_tls_keygen_workspace)); \\
    }} \\
  }} while (0)
#else
#define MLD_V23B_CLEAN_KEYGEN_WORKSPACE() \\
  do {{ \\
  }} while (0)
#endif

#endif /* MLD_CONFIG_EXPERIMENTAL_CALLER_KEYGEN_WORKSPACE */

"""


for path, prefix in TARGETS:
    text = path.read_text()

    backup = path.with_suffix(path.suffix + ".before_v23b")
    if not backup.exists():
        backup.write_text(text)

    if f"{prefix}_v23b_keygen_workspace_bytes" not in text:
        if V22B_MARKER not in text:
            raise SystemExit(f"cannot find v22b marker in {path}")
        text = text.replace(V22B_MARKER, V22B_MARKER + v23b_block(prefix), 1)
    else:
        print(f"v23b block already present in {path}")

    if OLD_KEYPAIR_ALLOC in text:
        text = text.replace(OLD_KEYPAIR_ALLOC, NEW_KEYPAIR_ALLOC, 1)
    elif "MLD_V23B_REQUIRE_KEYGEN_WORKSPACE();" in text:
        print(f"keypair allocation already patched in {path}")
    else:
        raise SystemExit(f"cannot find keypair allocation block in {path}")

    if OLD_KEYPAIR_CLEANUP in text:
        text = text.replace(OLD_KEYPAIR_CLEANUP, NEW_KEYPAIR_CLEANUP, 1)
    elif "MLD_V23B_CLEAN_KEYGEN_WORKSPACE();" in text:
        print(f"keypair cleanup already patched in {path}")
    else:
        raise SystemExit(f"cannot find keypair cleanup block in {path}")

    if OLD_PK_ALLOC in text:
        text = text.replace(OLD_PK_ALLOC, NEW_PK_ALLOC, 1)
    elif "mld_v23b_tls_keygen_workspace->t0_packed" in text:
        print(f"pk_from_sk allocation already patched in {path}")
    else:
        raise SystemExit(f"cannot find pk_from_sk allocation block in {path}")

    if OLD_PK_CLEANUP in text:
        text = text.replace(OLD_PK_CLEANUP, NEW_PK_CLEANUP, 1)
    elif "MLD_V23B_CLEAN_KEYGEN_WORKSPACE();" in text:
        print(f"pk_from_sk cleanup already patched in {path}")
    else:
        raise SystemExit(f"cannot find pk_from_sk cleanup block in {path}")

    path.write_text(text)
    print(f"patched {path}")
