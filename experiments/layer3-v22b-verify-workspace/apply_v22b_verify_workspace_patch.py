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

V21_MARKER = "#endif /* MLD_CONFIG_EXPERIMENTAL_UNIFIED_SIGN_WORKSPACE */\n\n"

OLD_ALLOC = """  MLD_ALLOC(buf, uint8_t, (MLDSA_K * MLDSA_POLYW1_PACKEDBYTES), context);
  MLD_ALLOC(mu, uint8_t, MLDSA_CRHBYTES, context);
  MLD_ALLOC(c, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_ALLOC(c2, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_ALLOC(z, mld_polyvecl, 1, context);
  MLD_ALLOC(cp, mld_poly, 1, context);
  MLD_V17B_ALLOC_MAT(mat);
  MLD_ALLOC(w1, mld_poly, 1, context);
  MLD_ALLOC(tmp, mld_poly, 1, context);
"""

NEW_ALLOC = """#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE)
  MLD_V22B_REQUIRE_VERIFY_WORKSPACE();

  uint8_t *buf = mld_v22b_tls_verify_workspace->buf;
  uint8_t *mu = mld_v22b_tls_verify_workspace->mu;
  uint8_t *c = mld_v22b_tls_verify_workspace->c;
  uint8_t *c2 = mld_v22b_tls_verify_workspace->c2;
  mld_polyvecl *z = &mld_v22b_tls_verify_workspace->z;
  mld_poly *cp = &mld_v22b_tls_verify_workspace->cp;
  MLD_V17B_ALLOC_MAT(mat);
  mld_poly *w1 = &mld_v22b_tls_verify_workspace->w1;
  mld_poly *tmp = &mld_v22b_tls_verify_workspace->tmp;
#else
  MLD_ALLOC(buf, uint8_t, (MLDSA_K * MLDSA_POLYW1_PACKEDBYTES), context);
  MLD_ALLOC(mu, uint8_t, MLDSA_CRHBYTES, context);
  MLD_ALLOC(c, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_ALLOC(c2, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_ALLOC(z, mld_polyvecl, 1, context);
  MLD_ALLOC(cp, mld_poly, 1, context);
  MLD_V17B_ALLOC_MAT(mat);
  MLD_ALLOC(w1, mld_poly, 1, context);
  MLD_ALLOC(tmp, mld_poly, 1, context);
#endif
"""

OLD_HPK = """    MLD_ALIGN uint8_t hpk[MLDSA_CRHBYTES];
    mld_H(hpk, MLDSA_TRBYTES, pk, MLDSA_CRYPTO_PUBLICKEYBYTES, NULL, 0, NULL,
          0);
    mld_H(mu, MLDSA_CRHBYTES, hpk, MLDSA_TRBYTES, pre, prelen, m, mlen);

    /* @[FIPS204, Section 3.6.3] Destruction of intermediate values. */
    mld_zeroize(hpk, sizeof(hpk));
"""

NEW_HPK = """#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE)
    uint8_t *hpk = mld_v22b_tls_verify_workspace->hpk;
#else
    MLD_ALIGN uint8_t hpk[MLDSA_CRHBYTES];
#endif
    mld_H(hpk, MLDSA_TRBYTES, pk, MLDSA_CRYPTO_PUBLICKEYBYTES, NULL, 0, NULL,
          0);
    mld_H(mu, MLDSA_CRHBYTES, hpk, MLDSA_TRBYTES, pre, prelen, m, mlen);

    /* @[FIPS204, Section 3.6.3] Destruction of intermediate values. */
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE)
    mld_zeroize(hpk, MLDSA_CRHBYTES);
#else
    mld_zeroize(hpk, sizeof(hpk));
#endif
"""

OLD_CLEANUP = """cleanup:
  /* @[FIPS204, Section 3.6.3] Destruction of intermediate values. */
  MLD_FREE(tmp, mld_poly, 1, context);
  MLD_FREE(w1, mld_poly, 1, context);
  MLD_V17B_FREE_MAT(mat);
  MLD_FREE(cp, mld_poly, 1, context);
  MLD_FREE(z, mld_polyvecl, 1, context);
  MLD_FREE(c2, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_FREE(c, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_FREE(mu, uint8_t, MLDSA_CRHBYTES, context);
  MLD_FREE(buf, uint8_t, (MLDSA_K * MLDSA_POLYW1_PACKEDBYTES), context);
  return ret;
"""

NEW_CLEANUP = """cleanup:
  /* @[FIPS204, Section 3.6.3] Destruction of intermediate values. */
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE)
  MLD_V22B_CLEAN_VERIFY_WORKSPACE();
#else
  MLD_FREE(tmp, mld_poly, 1, context);
  MLD_FREE(w1, mld_poly, 1, context);
#endif
  MLD_V17B_FREE_MAT(mat);
#if !defined(MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE)
  MLD_FREE(cp, mld_poly, 1, context);
  MLD_FREE(z, mld_polyvecl, 1, context);
  MLD_FREE(c2, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_FREE(c, uint8_t, MLDSA_CTILDEBYTES, context);
  MLD_FREE(mu, uint8_t, MLDSA_CRHBYTES, context);
  MLD_FREE(buf, uint8_t, (MLDSA_K * MLDSA_POLYW1_PACKEDBYTES), context);
#endif
  return ret;
"""


def v22b_block(prefix: str) -> str:
    return f"""
#if defined(MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE)

/*
 * v22b caller-provided verification workspace.
 *
 * v22a showed that verify_internal is dominated by local verification buffers:
 * z, cp, w1, tmp, buf, mu, c, c2, plus hpk.
 *
 * v22b moves those buffers out of the function stack and into explicit
 * caller-owned workspace.
 */
typedef struct {{
  MLD_ALIGN mld_polyvecl z;
  MLD_ALIGN mld_poly cp;
  MLD_ALIGN mld_poly w1;
  MLD_ALIGN mld_poly tmp;
  MLD_ALIGN uint8_t buf[MLDSA_K * MLDSA_POLYW1_PACKEDBYTES];
  MLD_ALIGN uint8_t mu[MLDSA_CRHBYTES];
  MLD_ALIGN uint8_t c[MLDSA_CTILDEBYTES];
  MLD_ALIGN uint8_t c2[MLDSA_CTILDEBYTES];
  MLD_ALIGN uint8_t hpk[MLDSA_CRHBYTES];
}} mld_v22b_verify_workspace;

static _Thread_local mld_v22b_verify_workspace *mld_v22b_tls_verify_workspace;

size_t {prefix}_v22b_verify_workspace_bytes(void) {{
  return sizeof(mld_v22b_verify_workspace);
}}

int {prefix}_v22b_verify_workspace_set(void *workspace, size_t workspace_bytes) {{
  if (workspace == 0 || workspace_bytes < sizeof(mld_v22b_verify_workspace)) {{
    return -1;
  }}

  if ((((uintptr_t)workspace) & (uintptr_t)63u) != 0u) {{
    return -2;
  }}

  mld_v22b_tls_verify_workspace = (mld_v22b_verify_workspace *)workspace;
  return 0;
}}

#define MLD_V22B_REQUIRE_VERIFY_WORKSPACE() \\
  do {{ \\
    if (mld_v22b_tls_verify_workspace == 0) {{ \\
      return MLD_ERR_OUT_OF_MEMORY; \\
    }} \\
  }} while (0)

#if defined(MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE)
static void mld_v22b_cleanse(void *ptr, size_t len) {{
  volatile uint8_t *p = (volatile uint8_t *)ptr;

  while (len > 0) {{
    *p++ = 0;
    len--;
  }}
}}

#define MLD_V22B_CLEAN_VERIFY_WORKSPACE() \\
  do {{ \\
    if (mld_v22b_tls_verify_workspace != 0) {{ \\
      mld_v22b_cleanse(mld_v22b_tls_verify_workspace, \\
                       sizeof(*mld_v22b_tls_verify_workspace)); \\
    }} \\
  }} while (0)
#else
#define MLD_V22B_CLEAN_VERIFY_WORKSPACE() \\
  do {{ \\
  }} while (0)
#endif

#endif /* MLD_CONFIG_EXPERIMENTAL_CALLER_VERIFY_WORKSPACE */

"""


for path, prefix in TARGETS:
    text = path.read_text()

    backup = path.with_suffix(path.suffix + ".before_v22b")
    if not backup.exists():
        backup.write_text(text)

    if f"{prefix}_v22b_verify_workspace_bytes" not in text:
        if V21_MARKER not in text:
            raise SystemExit(f"cannot find v21 marker in {path}")
        text = text.replace(V21_MARKER, V21_MARKER + v22b_block(prefix), 1)
    else:
        print(f"v22b block already present in {path}")

    if OLD_ALLOC in text:
        text = text.replace(OLD_ALLOC, NEW_ALLOC, 1)
    elif "MLD_V22B_REQUIRE_VERIFY_WORKSPACE();" in text:
        print(f"allocation block already patched in {path}")
    else:
        raise SystemExit(f"cannot find verify allocation block in {path}")

    if OLD_HPK in text:
        text = text.replace(OLD_HPK, NEW_HPK, 1)
    elif "mld_v22b_tls_verify_workspace->hpk" in text:
        print(f"hpk block already patched in {path}")
    else:
        raise SystemExit(f"cannot find hpk block in {path}")

    if OLD_CLEANUP in text:
        text = text.replace(OLD_CLEANUP, NEW_CLEANUP, 1)
    elif "MLD_V22B_CLEAN_VERIFY_WORKSPACE();" in text:
        print(f"cleanup block already patched in {path}")
    else:
        raise SystemExit(f"cannot find cleanup block in {path}")

    path.write_text(text)
    print(f"patched {path}")
