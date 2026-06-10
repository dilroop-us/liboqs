#!/usr/bin/env python3
from pathlib import Path

path = Path.home() / "pqc/liboqs/experiments/layer3-v16-caller-matrix-workspace/v16_operation_profiler.c"
text = path.read_text()

INSERT = r'''
/*
 * v16 caller-provided workspace integration.
 *
 * These symbols only exist in the v16 liboqs build.
 * They are weak so the same profiler source can still link against
 * baseline and reduced-RAM libraries.
 */
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes(void) __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_set(void *workspace, size_t workspace_bytes) __attribute__((weak));

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_bytes(void) __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_set(void *workspace, size_t workspace_bytes) __attribute__((weak));

static void *v16_x86_workspace = 0;
static void *v16_ref_workspace = 0;

static void *v16_alloc_aligned(size_t bytes) {
  void *ptr = 0;
  if (posix_memalign(&ptr, 64, bytes) != 0) {
    return 0;
  }
  return ptr;
}

static void v16_setup_workspace_if_available(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes();

    if (v16_x86_workspace == 0) {
      v16_x86_workspace = v16_alloc_aligned(bytes);
      if (v16_x86_workspace == 0) {
        fprintf(stderr, "failed to allocate v16 x86_64 workspace\n");
        exit(1);
      }
    }

    if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_set(v16_x86_workspace, bytes) != 0) {
      fprintf(stderr, "failed to set v16 x86_64 workspace\n");
      exit(1);
    }
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_bytes();

    if (v16_ref_workspace == 0) {
      v16_ref_workspace = v16_alloc_aligned(bytes);
      if (v16_ref_workspace == 0) {
        fprintf(stderr, "failed to allocate v16 ref workspace\n");
        exit(1);
      }
    }

    if (PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_set(v16_ref_workspace, bytes) != 0) {
      fprintf(stderr, "failed to set v16 ref workspace\n");
      exit(1);
    }
  }
}

'''

if "v16_setup_workspace_if_available" not in text:
    # Insert after includes. Use first blank line after include block.
    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("#include"):
            insert_at = i + 1
    lines.insert(insert_at, INSERT)
    text = "\n".join(lines) + "\n"

needle = "OQS_SIG *sig = OQS_SIG_new(OQS_SIG_alg_ml_dsa_44);\n"
replacement = needle + "  v16_setup_workspace_if_available();\n"

if "v16_setup_workspace_if_available();" not in text:
    text = text.replace(needle, replacement)

path.write_text(text)
print(f"patched {path}")
