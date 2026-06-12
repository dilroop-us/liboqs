#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"

TARGETS = [
    ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c",
    ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c",
]

CLEANSE_INSERT_AFTER = "static _Thread_local mld_v17b_sign_workspace *mld_v17b_tls_workspace;"

CLEANSE_FUNCTION = r'''

#if defined(MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE)
static void mld_v18_cleanse(void *ptr, size_t len) {
  volatile uint8_t *p = (volatile uint8_t *)ptr;

  while (len > 0) {
    *p++ = 0;
    len--;
  }
}
#endif
'''

OLD_FREE_MAT = r'''#define MLD_V17B_FREE_MAT(name) \
  do { (void)(name); } while (0)'''

NEW_FREE_MAT = r'''#if defined(MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE)
#define MLD_V17B_FREE_MAT(name) \
  do { \
    (void)(name); \
    if (mld_v17b_tls_workspace != 0) { \
      mld_v18_cleanse(mld_v17b_tls_workspace, sizeof(*mld_v17b_tls_workspace)); \
    } \
  } while (0)
#else
#define MLD_V17B_FREE_MAT(name) \
  do { (void)(name); } while (0)
#endif'''

for path in TARGETS:
    text = path.read_text()

    if "mld_v18_cleanse" not in text:
        if CLEANSE_INSERT_AFTER not in text:
            raise SystemExit(f"cannot find insert point in {path}")

        text = text.replace(
            CLEANSE_INSERT_AFTER,
            CLEANSE_INSERT_AFTER + CLEANSE_FUNCTION,
            1,
        )

    if "MLD_CONFIG_EXPERIMENTAL_WORKSPACE_SANITIZE" not in text.split("#elif defined(MLD_CONFIG_EXPERIMENTAL_CALLER_MATRIX_WORKSPACE)")[0]:
        raise SystemExit(f"sanitize block did not land inside caller-sign branch in {path}")

    # Replace only the first FREE_MAT no-op, which belongs to the caller sign workspace branch.
    if NEW_FREE_MAT not in text:
        if OLD_FREE_MAT not in text:
            raise SystemExit(f"cannot find MLD_V17B_FREE_MAT no-op in {path}")

        text = text.replace(OLD_FREE_MAT, NEW_FREE_MAT, 1)

    path.write_text(text)
    print(f"patched {path}")
