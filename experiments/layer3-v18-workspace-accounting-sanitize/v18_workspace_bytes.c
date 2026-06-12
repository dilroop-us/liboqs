#include <stddef.h>
#include <stdio.h>

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes(void) __attribute__((weak));
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes(void) __attribute__((weak));

int main(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes) {
    printf("caller_matrix_workspace_bytes,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes());
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes) {
    printf("caller_sign_workspace_bytes,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes());
  }

  return 0;
}
