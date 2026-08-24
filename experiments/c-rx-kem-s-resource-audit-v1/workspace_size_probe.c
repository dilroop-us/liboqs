#include <stddef.h>
#include <stdio.h>

/* Reference C implementation */

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_C_v26_enc_workspace_bytes(void);

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_C_v27_keypair_workspace_bytes(void);

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_C_v28_dec_workspace_bytes(void);

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes(void);


/* x86_64 implementation */

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v26_enc_workspace_bytes(void);

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v27_keypair_workspace_bytes(void);

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v28_dec_workspace_bytes(void);

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes(void);


static void print_row(
    const char *implementation,
    const char *operation,
    size_t bytes
) {
    printf(
        "WORKSPACE_SIZE,%s,%s,%zu,%.2f\n",
        implementation,
        operation,
        bytes,
        (double) bytes / 1024.0
    );
}


int main(void) {
    print_row(
        "C",
        "v26_enc",
        PQCP_MLKEM_NATIVE_MLKEM768_C_v26_enc_workspace_bytes()
    );

    print_row(
        "C",
        "v27_keypair",
        PQCP_MLKEM_NATIVE_MLKEM768_C_v27_keypair_workspace_bytes()
    );

    print_row(
        "C",
        "v28_dec",
        PQCP_MLKEM_NATIVE_MLKEM768_C_v28_dec_workspace_bytes()
    );

    print_row(
        "C",
        "v29_lifecycle",
        PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes()
    );


    print_row(
        "X86_64",
        "v26_enc",
        PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v26_enc_workspace_bytes()
    );

    print_row(
        "X86_64",
        "v27_keypair",
        PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v27_keypair_workspace_bytes()
    );

    print_row(
        "X86_64",
        "v28_dec",
        PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v28_dec_workspace_bytes()
    );

    print_row(
        "X86_64",
        "v29_lifecycle",
        PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes()
    );

    return 0;
}
