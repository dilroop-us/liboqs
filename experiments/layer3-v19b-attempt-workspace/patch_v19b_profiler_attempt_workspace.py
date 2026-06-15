#!/usr/bin/env python3
import re
from pathlib import Path

p = Path("experiments/layer3-v19b-attempt-workspace/v19b_operation_profiler.c")
text = p.read_text()

# Ensure stdlib.h exists for posix_memalign/exit.
if "#include <stdlib.h>" not in text:
    text = text.replace("#include <stdio.h>", "#include <stdio.h>\n#include <stdlib.h>", 1)

INSERT = r'''
/* v19b caller-provided attempt-generation workspace support */
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v19b_attempt_workspace_bytes(void)
    __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v19b_attempt_workspace_set(void *workspace,
                                                                        size_t workspace_bytes)
    __attribute__((weak));

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v19b_attempt_workspace_bytes(void)
    __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_C_v19b_attempt_workspace_set(void *workspace,
                                                                  size_t workspace_bytes)
    __attribute__((weak));

static void *v19b_x86_attempt_workspace;
static void *v19b_c_attempt_workspace;

static void *v19b_alloc_aligned(size_t bytes) {
  void *ptr = NULL;

  if (posix_memalign(&ptr, 64, bytes) != 0) {
    return NULL;
  }

  return ptr;
}

static void v19b_setup_attempt_workspace_if_available(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v19b_attempt_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v19b_attempt_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v19b_attempt_workspace_bytes();

    if (v19b_x86_attempt_workspace == NULL) {
      v19b_x86_attempt_workspace = v19b_alloc_aligned(bytes);
    }

    if (v19b_x86_attempt_workspace == NULL ||
        PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v19b_attempt_workspace_set(
            v19b_x86_attempt_workspace, bytes) != 0) {
      fprintf(stderr, "failed to setup v19b x86_64 attempt workspace\n");
      exit(1);
    }
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_C_v19b_attempt_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_C_v19b_attempt_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_C_v19b_attempt_workspace_bytes();

    if (v19b_c_attempt_workspace == NULL) {
      v19b_c_attempt_workspace = v19b_alloc_aligned(bytes);
    }

    if (v19b_c_attempt_workspace == NULL ||
        PQCP_MLDSA_NATIVE_MLDSA44_C_v19b_attempt_workspace_set(
            v19b_c_attempt_workspace, bytes) != 0) {
      fprintf(stderr, "failed to setup v19b C attempt workspace\n");
      exit(1);
    }
  }
}

'''

# Insert helper after the include block.
if "v19b_setup_attempt_workspace_if_available" not in text:
    include_matches = list(re.finditer(r"^#include .*$", text, re.MULTILINE))
    if not include_matches:
        raise SystemExit("cannot find #include block")

    insert_pos = include_matches[-1].end()
    text = text[:insert_pos] + "\n" + INSERT + text[insert_pos:]

# Add setup call after every OQS_SIG_new(SIG_ALG).
lines = text.splitlines()
out = []
i = 0

while i < len(lines):
    out.append(lines[i])

    if "OQS_SIG *sig = OQS_SIG_new(SIG_ALG);" in lines[i]:
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if next_line != "v19b_setup_attempt_workspace_if_available();":
            indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
            out.append(indent + "v19b_setup_attempt_workspace_if_available();")

    i += 1

text = "\n".join(out) + "\n"

p.write_text(text)
print(f"patched {p}")
