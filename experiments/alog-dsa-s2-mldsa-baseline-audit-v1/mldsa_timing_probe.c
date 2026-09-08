#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

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

static volatile uint64_t audit_sink = 0;

static uint64_t now_ns(void)
{
    struct timespec ts;

#ifdef CLOCK_MONOTONIC_RAW
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) != 0) {
#else
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
#endif
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }

    return ((uint64_t)ts.tv_sec * UINT64_C(1000000000))
         + (uint64_t)ts.tv_nsec;
}

static void fill_message(
    uint8_t *message,
    size_t message_len,
    uint64_t iteration
)
{
    for (size_t i = 0; i < message_len; i++) {
        message[i] =
            (uint8_t)(
                0x5Au ^
                (uint8_t)i ^
                (uint8_t)(iteration * UINT64_C(131))
            );
    }
}

static void *alloc_workspace(size_t bytes)
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
    size_t samples = 5000;
    size_t warmup = 500;
    size_t message_len = 64;

    if (argc >= 2) {
        samples = (size_t)strtoull(argv[1], NULL, 10);
    }

    if (argc >= 3) {
        warmup = (size_t)strtoull(argv[2], NULL, 10);
    }

    if (argc >= 4) {
        message_len = (size_t)strtoull(argv[3], NULL, 10);
    }

    if (samples == 0 || message_len == 0) {
        fprintf(stderr, "invalid configuration\n");
        return 2;
    }

    OQS_SIG *sig = OQS_SIG_new(OQS_SIG_alg_ml_dsa_44);

    if (sig == NULL) {
        fprintf(stderr, "OQS_SIG_new failed\n");
        return 2;
    }

    const size_t c_ws =
        PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes();

    const size_t x86_ws =
        PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes();

    const size_t workspace_bytes =
        c_ws > x86_ws ? c_ws : x86_ws;

    void *workspace = alloc_workspace(workspace_bytes);

    uint8_t *pk = malloc(sig->length_public_key);
    uint8_t *sk = malloc(sig->length_secret_key);
    uint8_t *signature = malloc(sig->length_signature);
    uint8_t *message = malloc(message_len);

    if (
        workspace == NULL ||
        pk == NULL ||
        sk == NULL ||
        signature == NULL ||
        message == NULL
    ) {
        fprintf(stderr, "allocation failure\n");
        return 2;
    }

    const int c_set =
        PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_set(
            workspace,
            workspace_bytes
        );

    const int x86_set =
        PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_set(
            workspace,
            workspace_bytes
        );

    if (c_set != 0 || x86_set != 0) {
        fprintf(
            stderr,
            "workspace setter failure C=%d X86=%d\n",
            c_set,
            x86_set
        );
        return 2;
    }

    if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "keypair failure\n");
        return 2;
    }

    printf("TIMING_CONFIG,samples,%zu\n", samples);
    printf("TIMING_CONFIG,warmup,%zu\n", warmup);
    printf("TIMING_CONFIG,message_bytes,%zu\n", message_len);
    printf("TIMING_CONFIG,workspace_bytes,%zu\n", workspace_bytes);
    printf("TIMING_CONFIG,signature_bytes,%zu\n", sig->length_signature);

    /*
     * Signing warmup.
     */
    for (size_t i = 0; i < warmup; i++) {
        size_t signature_len = sig->length_signature;

        fill_message(message, message_len, i);

        if (
            OQS_SIG_sign(
                sig,
                signature,
                &signature_len,
                message,
                message_len,
                sk
            ) != OQS_SUCCESS
        ) {
            fprintf(stderr, "sign warmup failure\n");
            return 2;
        }

        audit_sink ^= signature[i % signature_len];
    }

    /*
     * Signing measurements.
     */
    for (size_t i = 0; i < samples; i++) {
        size_t signature_len = sig->length_signature;

        fill_message(message, message_len, i + warmup);

        const uint64_t start = now_ns();

        const OQS_STATUS rc =
            OQS_SIG_sign(
                sig,
                signature,
                &signature_len,
                message,
                message_len,
                sk
            );

        const uint64_t end = now_ns();

        if (rc == OQS_SUCCESS && signature_len > 0) {
            audit_sink ^= signature[i % signature_len];
        }

        printf(
            "SIGN_SAMPLE,%zu,%zu,%" PRIu64 ",%d\n",
            i,
            message_len,
            end - start,
            rc == OQS_SUCCESS ? 0 : 1
        );
    }

    /*
     * Prepare one valid message/signature pair for pure
     * verification measurement.
     */
    fill_message(message, message_len, UINT64_C(0xABCDEF));

    size_t signature_len = sig->length_signature;

    if (
        OQS_SIG_sign(
            sig,
            signature,
            &signature_len,
            message,
            message_len,
            sk
        ) != OQS_SUCCESS
    ) {
        fprintf(stderr, "verification setup sign failed\n");
        return 2;
    }

    /*
     * Verification warmup.
     */
    for (size_t i = 0; i < warmup; i++) {
        const OQS_STATUS rc =
            OQS_SIG_verify(
                sig,
                message,
                message_len,
                signature,
                signature_len,
                pk
            );

        if (rc != OQS_SUCCESS) {
            fprintf(stderr, "verify warmup failure\n");
            return 2;
        }

        audit_sink ^= (uint64_t)rc + i;
    }

    /*
     * Verification measurements.
     */
    for (size_t i = 0; i < samples; i++) {
        const uint64_t start = now_ns();

        const OQS_STATUS rc =
            OQS_SIG_verify(
                sig,
                message,
                message_len,
                signature,
                signature_len,
                pk
            );

        const uint64_t end = now_ns();

        audit_sink ^= (uint64_t)rc + i;

        printf(
            "VERIFY_SAMPLE,%zu,%zu,%" PRIu64 ",%d\n",
            i,
            message_len,
            end - start,
            rc == OQS_SUCCESS ? 0 : 1
        );
    }

    printf("TIMING_SINK,%" PRIu64 "\n", audit_sink);

    memset(workspace, 0, workspace_bytes);

    free(message);
    free(signature);
    free(sk);
    free(pk);
    free(workspace);

    OQS_SIG_free(sig);

    return 0;
}
