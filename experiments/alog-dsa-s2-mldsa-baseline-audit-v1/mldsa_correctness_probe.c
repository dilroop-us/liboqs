#define _POSIX_C_SOURCE 200112L

#include <oqs/oqs.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern size_t
PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes(void);

extern int
PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_set(
    void *workspace,
    size_t workspace_bytes
);

extern size_t
PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes(void);

extern int
PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_set(
    void *workspace,
    size_t workspace_bytes
);

static void fill_message(uint8_t *msg, size_t len, int iteration)
{
    for (size_t i = 0; i < len; i++) {
        msg[i] =
            (uint8_t)(
                0xA5u ^
                (uint8_t)i ^
                (uint8_t)(iteration * 131)
            );
    }
}

static void *aligned_workspace(size_t bytes)
{
    void *ptr = NULL;

    if (posix_memalign(&ptr, 64, bytes) != 0 || ptr == NULL) {
        return NULL;
    }

    memset(ptr, 0, bytes);
    return ptr;
}

int main(int argc, char **argv)
{
    int iterations = 10;

    if (argc >= 2) {
        iterations = atoi(argv[1]);
    }

    if (iterations <= 0) {
        fprintf(stderr, "iterations must be positive\n");
        return 2;
    }

    OQS_SIG *sig = OQS_SIG_new(OQS_SIG_alg_ml_dsa_44);

    if (sig == NULL) {
        fprintf(stderr, "ERROR,OQS_SIG_new\n");
        return 2;
    }

    const size_t c_ws =
        PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes();

    const size_t x86_ws =
        PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes();

    const size_t workspace_bytes =
        c_ws > x86_ws ? c_ws : x86_ws;

    void *workspace = aligned_workspace(workspace_bytes);

    if (workspace == NULL) {
        fprintf(stderr, "ERROR,workspace_allocation\n");
        OQS_SIG_free(sig);
        return 2;
    }

    int c_set =
        PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_set(
            workspace,
            workspace_bytes
        );

    int x86_set =
        PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_set(
            workspace,
            workspace_bytes
        );

    printf("AUDIT_CONFIG,iterations,%d\n", iterations);
    printf("AUDIT_CONFIG,workspace_bytes,%zu\n", workspace_bytes);
    printf("AUDIT_CONFIG,C_workspace_set,%d\n", c_set);
    printf("AUDIT_CONFIG,X86_64_workspace_set,%d\n", x86_set);

    if (c_set != 0 || x86_set != 0) {
        fprintf(stderr, "ERROR,workspace_set\n");
        free(workspace);
        OQS_SIG_free(sig);
        return 2;
    }

    uint8_t *pk =
        malloc(sig->length_public_key);

    uint8_t *sk =
        malloc(sig->length_secret_key);

    uint8_t *wrong_pk =
        malloc(sig->length_public_key);

    uint8_t *wrong_sk =
        malloc(sig->length_secret_key);

    /*
     * Allocate one extra byte so we can safely test an
     * over-length signature.
     */
    uint8_t *signature =
        malloc(sig->length_signature + 1);

    uint8_t message[64];
    uint8_t modified_message[64];

    if (
        pk == NULL ||
        sk == NULL ||
        wrong_pk == NULL ||
        wrong_sk == NULL ||
        signature == NULL
    ) {
        fprintf(stderr, "ERROR,allocation\n");
        return 2;
    }

    if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "ERROR,keypair\n");
        return 2;
    }

    if (OQS_SIG_keypair(sig, wrong_pk, wrong_sk) != OQS_SUCCESS) {
        fprintf(stderr, "ERROR,wrong_keypair\n");
        return 2;
    }

    int valid_pass = 0;
    int valid_fail = 0;

    int modified_message_pass = 0;
    int modified_message_fail = 0;

    int modified_signature_pass = 0;
    int modified_signature_fail = 0;

    int wrong_key_pass = 0;
    int wrong_key_fail = 0;

    int truncated_pass = 0;
    int truncated_fail = 0;

    int extended_pass = 0;
    int extended_fail = 0;

    int zero_signature_pass = 0;
    int zero_signature_fail = 0;

    for (int iteration = 0; iteration < iterations; iteration++) {

        fill_message(message, sizeof(message), iteration);

        size_t signature_len = sig->length_signature;

        memset(signature, 0, sig->length_signature + 1);

        if (
            OQS_SIG_sign(
                sig,
                signature,
                &signature_len,
                message,
                sizeof(message),
                sk
            ) != OQS_SUCCESS
        ) {
            printf(
                "AUDIT_FAIL,iteration=%d,sign\n",
                iteration
            );

            valid_fail++;
            continue;
        }

        /*
         * Valid signature.
         */
        if (
            OQS_SIG_verify(
                sig,
                message,
                sizeof(message),
                signature,
                signature_len,
                pk
            ) == OQS_SUCCESS
        ) {
            valid_pass++;
        } else {
            valid_fail++;
        }

        /*
         * Modified message.
         */
        memcpy(
            modified_message,
            message,
            sizeof(message)
        );

        modified_message[0] ^= 0x01u;

        if (
            OQS_SIG_verify(
                sig,
                modified_message,
                sizeof(modified_message),
                signature,
                signature_len,
                pk
            ) != OQS_SUCCESS
        ) {
            modified_message_pass++;
        } else {
            modified_message_fail++;
        }

        /*
         * Modified signature.
         */
        signature[0] ^= 0x01u;

        if (
            OQS_SIG_verify(
                sig,
                message,
                sizeof(message),
                signature,
                signature_len,
                pk
            ) != OQS_SUCCESS
        ) {
            modified_signature_pass++;
        } else {
            modified_signature_fail++;
        }

        signature[0] ^= 0x01u;

        /*
         * Wrong public key.
         */
        if (
            OQS_SIG_verify(
                sig,
                message,
                sizeof(message),
                signature,
                signature_len,
                wrong_pk
            ) != OQS_SUCCESS
        ) {
            wrong_key_pass++;
        } else {
            wrong_key_fail++;
        }

        /*
         * Truncated signature.
         */
        if (
            signature_len > 0 &&
            OQS_SIG_verify(
                sig,
                message,
                sizeof(message),
                signature,
                signature_len - 1,
                pk
            ) != OQS_SUCCESS
        ) {
            truncated_pass++;
        } else {
            truncated_fail++;
        }

        /*
         * Extended signature.
         */
        signature[signature_len] = 0x5Au;

        if (
            OQS_SIG_verify(
                sig,
                message,
                sizeof(message),
                signature,
                signature_len + 1,
                pk
            ) != OQS_SUCCESS
        ) {
            extended_pass++;
        } else {
            extended_fail++;
        }

        /*
         * Zero signature.
         */
        uint8_t saved_first = signature[0];

        memset(
            signature,
            0,
            signature_len
        );

        if (
            OQS_SIG_verify(
                sig,
                message,
                sizeof(message),
                signature,
                signature_len,
                pk
            ) != OQS_SUCCESS
        ) {
            zero_signature_pass++;
        } else {
            zero_signature_fail++;
        }

        /*
         * saved_first is intentionally unused afterwards because
         * the next iteration generates a new signature.
         */
        (void)saved_first;
    }

#define PRINT_RESULT(name, pass, fail) \
    printf( \
        "AUDIT_CASE,%s,%d,%d,%s\n", \
        name, \
        pass, \
        fail, \
        ((fail) == 0 && (pass) == iterations) ? "PASS" : "FAIL" \
    )

    PRINT_RESULT(
        "valid_sign_verify",
        valid_pass,
        valid_fail
    );

    PRINT_RESULT(
        "modified_message_rejected",
        modified_message_pass,
        modified_message_fail
    );

    PRINT_RESULT(
        "modified_signature_rejected",
        modified_signature_pass,
        modified_signature_fail
    );

    PRINT_RESULT(
        "wrong_public_key_rejected",
        wrong_key_pass,
        wrong_key_fail
    );

    PRINT_RESULT(
        "truncated_signature_rejected",
        truncated_pass,
        truncated_fail
    );

    PRINT_RESULT(
        "extended_signature_rejected",
        extended_pass,
        extended_fail
    );

    PRINT_RESULT(
        "zero_signature_rejected",
        zero_signature_pass,
        zero_signature_fail
    );

    const int total_failures =
        valid_fail +
        modified_message_fail +
        modified_signature_fail +
        wrong_key_fail +
        truncated_fail +
        extended_fail +
        zero_signature_fail;

    printf(
        "AUDIT_SUMMARY,%d,%s\n",
        total_failures,
        total_failures == 0 ? "PASS" : "FAIL"
    );

    free(signature);
    free(wrong_sk);
    free(wrong_pk);
    free(sk);
    free(pk);

    memset(workspace, 0, workspace_bytes);
    free(workspace);

    OQS_SIG_free(sig);

    return total_failures == 0 ? 0 : 1;
}
