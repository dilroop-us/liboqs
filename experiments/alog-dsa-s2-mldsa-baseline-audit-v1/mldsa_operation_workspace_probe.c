#include <stddef.h>
#include <stdio.h>

/* C backend */
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v19b_attempt_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v21_sign_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v22b_verify_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v23b_keygen_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes(void);

/* x86-64 backend */
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v19b_attempt_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v23b_keygen_workspace_bytes(void);
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes(void);

static void print_row(const char *backend,
                      const char *name,
                      size_t bytes)
{
    printf("WORKSPACE_SIZE,%s,%s,%zu,%.2f\n",
           backend,
           name,
           bytes,
           (double)bytes / 1024.0);
}

static void print_c(void)
{
    print_row("C", "v17b_sign_core",
              PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_bytes());

    print_row("C", "v19b_attempt",
              PQCP_MLDSA_NATIVE_MLDSA44_C_v19b_attempt_workspace_bytes());

    print_row("C", "v21_sign_total",
              PQCP_MLDSA_NATIVE_MLDSA44_C_v21_sign_workspace_bytes());

    print_row("C", "v22b_verify_region",
              PQCP_MLDSA_NATIVE_MLDSA44_C_v22b_verify_workspace_bytes());

    print_row("C", "v23b_keygen_region",
              PQCP_MLDSA_NATIVE_MLDSA44_C_v23b_keygen_workspace_bytes());

    print_row("C", "v24_lifecycle",
              PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes());
}

static void print_x86(void)
{
    print_row("X86_64", "v17b_sign_core",
              PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes());

    print_row("X86_64", "v19b_attempt",
              PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v19b_attempt_workspace_bytes());

    print_row("X86_64", "v21_sign_total",
              PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes());

    print_row("X86_64", "v22b_verify_region",
              PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v22b_verify_workspace_bytes());

    print_row("X86_64", "v23b_keygen_region",
              PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v23b_keygen_workspace_bytes());

    print_row("X86_64", "v24_lifecycle",
              PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes());
}

int main(void)
{
    print_c();
    print_x86();
    return 0;
}
