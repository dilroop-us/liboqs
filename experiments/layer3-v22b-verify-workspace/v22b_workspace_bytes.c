#include <stddef.h>
#include <stdio.h>

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes(void)
    __attribute__((weak));
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes(void)
    __attribute__((weak));

int main(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes) {
    printf("unified_sign_workspace_bytes,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes());
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes) {
    printf("verify_workspace_bytes,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes());
  }

  return 0;
}
