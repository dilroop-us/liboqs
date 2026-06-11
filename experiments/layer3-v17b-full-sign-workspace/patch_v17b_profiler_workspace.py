#!/usr/bin/env python3
from pathlib import Path

path = Path.home() / "pqc/liboqs/experiments/layer3-v17b-full-sign-workspace/v17b_operation_profiler.c"
text = path.read_text()

INSERT = r'''
/*
 * v17b caller-provided full signing workspace integration.
 *
 * These symbols only exist in the v17b liboqs build.
 * They are weak so this profiler can still link against baseline,
 * reduced-RAM, v15, and v16 libraries.
 */
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes(void) __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_set(void *workspace, size_t workspace_bytes) __attribute__((weak));

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_bytes(void) __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_set(void *workspace, size_t workspace_bytes) __attribute__((weak));

static void *v17b_x86_workspace = 0;
static void *v17b_ref_workspace = 0;

static void *v17b_alloc_aligned(size_t bytes) {
  void *ptr = 0;
  if (posix_memalign(&ptr, 64, bytes) != 0) {
    return 0;
  }
  return ptr;
}

static void v17b_setup_workspace_if_available(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes();

    if (v17b_x86_workspace == 0) {
      v17b_x86_workspace = v17b_alloc_aligned(bytes);
      if (v17b_x86_workspace == 0) {
        fprintf(stderr, "failed to allocate v17b x86_64 signing workspace\n");
        exit(1);
      }
    }

    if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_set(v17b_x86_workspace, bytes) != 0) {
      fprintf(stderr, "failed to set v17b x86_64 signing workspace\n");
      exit(1);
    }
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_bytes();

    if (v17b_ref_workspace == 0) {
      v17b_ref_workspace = v17b_alloc_aligned(bytes);
      if (v17b_ref_workspace == 0) {
        fprintf(stderr, "failed to allocate v17b ref signing workspace\n");
        exit(1);
      }
    }

    if (PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_set(v17b_ref_workspace, bytes) != 0) {
      fprintf(stderr, "failed to set v17b ref signing workspace\n");
      exit(1);
    }
  }
}

'''

if "v17b_setup_workspace_if_available" not in text:
    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("#include"):
            insert_at = i + 1
    lines.insert(insert_at, INSERT)
    text = "\n".join(lines) + "\n"

lines = text.splitlines()
new_lines = []
inside_oqs_sig_new = False
inserted = 0

for i, line in enumerate(lines):
    new_lines.append(line)

    if "OQS_SIG_new" in line:
        inside_oqs_sig_new = True

    if inside_oqs_sig_new and ";" in line:
        nearby = "\n".join(lines[i+1:i+8])
        if "v17b_setup_workspace_if_available();" not in nearby:
            new_lines.append("  v17b_setup_workspace_if_available();")
            inserted += 1
        inside_oqs_sig_new = False

path.write_text("\n".join(new_lines) + "\n")
print(f"patched {path}")
print(f"inserted v17b setup calls: {inserted}")
