#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"

FILES = [
    ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c",
    ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c",
]

INSERT_MARKER = "static void mld_sample_s1_s2"

V15_BLOCK = r'''
/*
 * Layer 3 v15 experiment:
 *
 * Static matrix workspace prototype.
 *
 * This keeps the eager matrix path but moves the large mld_polymat
 * workspace out of the stack when MLD_CONFIG_EXPERIMENTAL_STATIC_MATRIX_WORKSPACE
 * is enabled.
 *
 * This is an experimental single-operation/IoT-style prototype.
 * It is not thread-safe and should not be treated as production API design.
 */
#if defined(MLD_CONFIG_EXPERIMENTAL_STATIC_MATRIX_WORKSPACE)
static MLD_ALIGN mld_polymat mld_v15_static_mat;

#define MLD_V15_ALLOC_MAT(name) \
  mld_polymat *name = &mld_v15_static_mat

#define MLD_V15_FREE_MAT(name) \
  do { (void)(name); } while (0)
#else
#define MLD_V15_ALLOC_MAT(name) \
  MLD_ALLOC(name, mld_polymat, 1, context)

#define MLD_V15_FREE_MAT(name) \
  MLD_FREE(name, mld_polymat, 1, context)
#endif

'''

for path in FILES:
    text = path.read_text()

    if "MLD_CONFIG_EXPERIMENTAL_STATIC_MATRIX_WORKSPACE" not in text:
        marker_index = text.find(INSERT_MARKER)
        if marker_index == -1:
            raise SystemExit(f"marker not found in {path}")

        text = text[:marker_index] + V15_BLOCK + text[marker_index:]

    alloc_old = "MLD_ALLOC(mat, mld_polymat, 1, context);"
    free_old = "MLD_FREE(mat, mld_polymat, 1, context);"

    alloc_count = text.count(alloc_old)
    free_count = text.count(free_old)

    text = text.replace(alloc_old, "MLD_V15_ALLOC_MAT(mat);")
    text = text.replace(free_old, "MLD_V15_FREE_MAT(mat);")

    path.write_text(text)

    print(f"patched {path}")
    print(f"  replaced allocs: {alloc_count}")
    print(f"  replaced frees : {free_count}")
