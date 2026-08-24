#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes(void);

extern int
PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_set(
    uint8_t *ptr,
    size_t len
);

extern size_t
PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes(void);

extern int
PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_set(
    uint8_t *ptr,
    size_t len
);

static uint64_t now_ns(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }

    return ((uint64_t)ts.tv_sec * UINT64_C(1000000000))
         + (uint64_t)ts.tv_nsec;
}

static size_t max_size(size_t a, size_t b) {
    return a > b ? a : b;
}

static uint8_t *alloc_aligned_workspace(size_t len) {
    void *ptr = NULL;

    if (posix_memalign(&ptr, 64, len) != 0 || ptr == NULL) {
        return NULL;
    }

    memset(ptr, 0, len);

    return (uint8_t *)ptr;
}

static int bind_workspace(
    uint8_t *workspace,
    size_t allocated_len,
    int *c_rc_out,
    int *x86_rc_out
) {
    const size_t c_len =
        PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes();

    const size_t x86_len =
        PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes();

    int c_rc = -999;
    int x86_rc = -999;

    if (c_len <= allocated_len) {
        c_rc =
            PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_set(
                workspace,
                c_len
            );
    }

    if (x86_len <= allocated_len) {
        x86_rc =
            PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_set(
                workspace,
                x86_len
            );
    }

    if (c_rc_out != NULL) {
        *c_rc_out = c_rc;
    }

    if (x86_rc_out != NULL) {
        *x86_rc_out = x86_rc;
    }

    return (c_rc == 0 || x86_rc == 0) ? 0 : -1;
}

int main(int argc, char **argv) {
    size_t iterations = 1000;

    if (argc > 1) {
        iterations = (size_t)strtoull(argv[1], NULL, 10);

        if (iterations == 0) {
            iterations = 1;
        }
    }

    OQS_init();

    OQS_KEM *kem = OQS_KEM_new("ML-KEM-768");

    if (kem == NULL) {
        fprintf(stderr, "OQS_KEM_new(ML-KEM-768) failed\n");
        OQS_destroy();
        return EXIT_FAILURE;
    }

    const size_t c_workspace =
        PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes();

    const size_t x86_workspace =
        PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes();

    const size_t workspace_len =
        max_size(c_workspace, x86_workspace);

    uint8_t *workspace =
        alloc_aligned_workspace(workspace_len);

    if (workspace == NULL) {
        fprintf(stderr, "workspace allocation failed\n");
        OQS_KEM_free(kem);
        OQS_destroy();
        return EXIT_FAILURE;
    }

    int c_setter_rc = -999;
    int x86_setter_rc = -999;

    if (bind_workspace(
            workspace,
            workspace_len,
            &c_setter_rc,
            &x86_setter_rc
        ) != 0) {

        fprintf(stderr, "all lifecycle workspace setters failed\n");

        free(workspace);
        OQS_KEM_free(kem);
        OQS_destroy();

        return EXIT_FAILURE;
    }

    printf("AUDIT_METRIC,iterations,%zu\n", iterations);
    printf("AUDIT_METRIC,alignment_bytes,64\n");

    printf(
        "AUDIT_METRIC,public_key_bytes,%zu\n",
        kem->length_public_key
    );

    printf(
        "AUDIT_METRIC,secret_key_bytes,%zu\n",
        kem->length_secret_key
    );

    printf(
        "AUDIT_METRIC,ciphertext_bytes,%zu\n",
        kem->length_ciphertext
    );

    printf(
        "AUDIT_METRIC,shared_secret_bytes,%zu\n",
        kem->length_shared_secret
    );

    printf(
        "AUDIT_METRIC,workspace_c_bytes,%zu\n",
        c_workspace
    );

    printf(
        "AUDIT_METRIC,workspace_x86_bytes,%zu\n",
        x86_workspace
    );

    printf(
        "AUDIT_METRIC,workspace_allocated_bytes,%zu\n",
        workspace_len
    );

    printf(
        "AUDIT_METRIC,setter_c_rc,%d\n",
        c_setter_rc
    );

    printf(
        "AUDIT_METRIC,setter_x86_rc,%d\n",
        x86_setter_rc
    );

    uint8_t *pk = malloc(kem->length_public_key);
    uint8_t *sk = malloc(kem->length_secret_key);
    uint8_t *ct = malloc(kem->length_ciphertext);
    uint8_t *ss_enc = malloc(kem->length_shared_secret);
    uint8_t *ss_dec = malloc(kem->length_shared_secret);

    if (
        pk == NULL ||
        sk == NULL ||
        ct == NULL ||
        ss_enc == NULL ||
        ss_dec == NULL
    ) {
        fprintf(stderr, "buffer allocation failed\n");

        free(pk);
        free(sk);
        free(ct);
        free(ss_enc);
        free(ss_dec);

        memset(workspace, 0, workspace_len);
        free(workspace);

        OQS_KEM_free(kem);
        OQS_destroy();

        return EXIT_FAILURE;
    }

    size_t passed = 0;
    size_t failed = 0;

    uint64_t total_decaps_ns = 0;
    uint64_t min_decaps_ns = UINT64_MAX;
    uint64_t max_decaps_ns = 0;

    for (size_t i = 0; i < iterations; i++) {

        if (bind_workspace(
                workspace,
                workspace_len,
                NULL,
                NULL
            ) != 0) {
            failed++;
            continue;
        }

        if (OQS_KEM_keypair(
                kem,
                pk,
                sk
            ) != OQS_SUCCESS) {
            failed++;
            continue;
        }

        if (bind_workspace(
                workspace,
                workspace_len,
                NULL,
                NULL
            ) != 0) {
            failed++;
            continue;
        }

        if (OQS_KEM_encaps(
                kem,
                ct,
                ss_enc,
                pk
            ) != OQS_SUCCESS) {
            failed++;
            continue;
        }

        if (bind_workspace(
                workspace,
                workspace_len,
                NULL,
                NULL
            ) != 0) {
            failed++;
            continue;
        }

        const uint64_t start = now_ns();

        const OQS_STATUS decaps_status =
            OQS_KEM_decaps(
                kem,
                ss_dec,
                ct,
                sk
            );

        const uint64_t end = now_ns();

        const uint64_t elapsed = end - start;

        total_decaps_ns += elapsed;

        if (elapsed < min_decaps_ns) {
            min_decaps_ns = elapsed;
        }

        if (elapsed > max_decaps_ns) {
            max_decaps_ns = elapsed;
        }

        if (decaps_status != OQS_SUCCESS) {
            failed++;
            continue;
        }

        if (memcmp(
                ss_enc,
                ss_dec,
                kem->length_shared_secret
            ) != 0) {
            failed++;
            continue;
        }

        passed++;
    }

    const uint64_t mean_decaps_ns =
        iterations > 0
            ? total_decaps_ns / iterations
            : 0;

    printf("AUDIT_METRIC,passed,%zu\n", passed);
    printf("AUDIT_METRIC,failed,%zu\n", failed);

    printf(
        "AUDIT_METRIC,decaps_mean_ns,%" PRIu64 "\n",
        mean_decaps_ns
    );

    printf(
        "AUDIT_METRIC,decaps_min_ns,%" PRIu64 "\n",
        min_decaps_ns == UINT64_MAX ? 0 : min_decaps_ns
    );

    printf(
        "AUDIT_METRIC,decaps_max_ns,%" PRIu64 "\n",
        max_decaps_ns
    );

    memset(sk, 0, kem->length_secret_key);
    memset(ss_enc, 0, kem->length_shared_secret);
    memset(ss_dec, 0, kem->length_shared_secret);
    memset(workspace, 0, workspace_len);

    free(pk);
    free(sk);
    free(ct);
    free(ss_enc);
    free(ss_dec);
    free(workspace);

    OQS_KEM_free(kem);
    OQS_destroy();

    return failed == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
