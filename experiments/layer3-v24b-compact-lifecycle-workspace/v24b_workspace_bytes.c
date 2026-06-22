#include <stddef.h>
#include <stdio.h>

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes(void) __attribute__((weak));
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes(void) __attribute__((weak));
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v23b_keygen_workspace_bytes(void) __attribute__((weak));
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes(void) __attribute__((weak));

int main(void) {
  size_t sign = 0;
  size_t verify = 0;
  size_t keygen = 0;
  size_t v24 = 0;

  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes) {
    sign = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes();
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes) {
    verify = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes();
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v23b_keygen_workspace_bytes) {
    keygen = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v23b_keygen_workspace_bytes();
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes) {
    v24 = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes();
  }

  printf("unified_sign_workspace,%zu\n", sign);
  printf("verify_workspace,%zu\n", verify);
  printf("keygen_workspace,%zu\n", keygen);
  printf("v23b_separate_total,%zu\n", sign + verify + keygen);
  printf("v24_lifecycle_workspace,%zu\n", v24);
  printf("saved_bytes,%zu\n", (sign + verify + keygen) > v24 ? (sign + verify + keygen) - v24 : 0);

  return 0;
}
