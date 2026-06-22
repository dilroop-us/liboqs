#include <stddef.h>
#include <stdio.h>

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes(void)
    __attribute__((weak));
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes(void)
    __attribute__((weak));
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v23b_keygen_workspace_bytes(void)
    __attribute__((weak));

int main(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes) {
    printf("unified_sign_workspace,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes());
  } else {
    printf("unified_sign_workspace,0\n");
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes) {
    printf("verify_workspace,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes());
  } else {
    printf("verify_workspace,0\n");
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v23b_keygen_workspace_bytes) {
    printf("keygen_workspace,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v23b_keygen_workspace_bytes());
  } else {
    printf("keygen_workspace,0\n");
  }

  return 0;
}
