#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "v37_workspace_setup.generated.h"

#ifdef OQS_KEM_alg_ml_kem_768
#define V37_MLKEM_ALG OQS_KEM_alg_ml_kem_768
#else
#define V37_MLKEM_ALG "ML-KEM-768"
#endif

#ifdef OQS_SIG_alg_ml_dsa_44
#define V37_MLDSA_ALG OQS_SIG_alg_ml_dsa_44
#else
#define V37_MLDSA_ALG "ML-DSA-44"
#endif

static uint64_t v37_rng_state = 0x3737371234567890ULL;

static uint64_t v37_xorshift64star(void) {
    uint64_t x = v37_rng_state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    v37_rng_state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

static void v37_randombytes(uint8_t *out, size_t outlen) {
    size_t i = 0;
    while (i < outlen) {
        uint64_t r = v37_xorshift64star();
        for (size_t j = 0; j < 8 && i < outlen; j++, i++) {
            out[i] = (uint8_t)(r >> (8 * j));
        }
    }
}

static void *xmalloc(size_t n) {
    void *p = malloc(n);
    if (p == NULL) {
        fprintf(stderr, "malloc failed for %zu bytes\n", n);
        exit(2);
    }
    return p;
}

static void *xaligned_malloc(size_t alignment, size_t n) {
    void *p = NULL;
    if (posix_memalign(&p, alignment, n) != 0 || p == NULL) {
        fprintf(stderr, "posix_memalign failed for %zu bytes with alignment %zu\n", n, alignment);
        exit(2);
    }
    return p;
}

static void fill_message(uint8_t *m, size_t mlen, int iter, uint8_t domain) {
    for (size_t i = 0; i < mlen; i++) {
        m[i] = (uint8_t)(domain ^ (uint8_t)i ^ (uint8_t)(iter * 131));
    }
}

#define V37_FAIL_POINT(build_case, component, iter, point) \
    fprintf(stderr, "V37_FAIL_POINT,%s,%s,iter=%d,%s\n", (build_case), (component), (iter), (point))

static int run_mlkem_once(const char *build_case, int iter) {
    OQS_KEM *kem = OQS_KEM_new(V37_MLKEM_ALG);
    if (kem == NULL) {
        V37_FAIL_POINT(build_case, "mlkem_valid_flow", iter, "OQS_KEM_new");
        return 1;
    }

    uint8_t *pk = xmalloc(kem->length_public_key);
    uint8_t *sk = xmalloc(kem->length_secret_key);
    uint8_t *ct = xmalloc(kem->length_ciphertext);
    uint8_t *ss1 = xmalloc(kem->length_shared_secret);
    uint8_t *ss2 = xmalloc(kem->length_shared_secret);

    int failed = 0;

    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "mlkem_valid_flow", iter, "OQS_KEM_keypair");
        failed = 1;
    }

    if (!failed && OQS_KEM_encaps(kem, ct, ss1, pk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "mlkem_valid_flow", iter, "OQS_KEM_encaps");
        failed = 1;
    }

    if (!failed && OQS_KEM_decaps(kem, ss2, ct, sk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "mlkem_valid_flow", iter, "OQS_KEM_decaps");
        failed = 1;
    }

    if (!failed && memcmp(ss1, ss2, kem->length_shared_secret) != 0) {
        V37_FAIL_POINT(build_case, "mlkem_valid_flow", iter, "shared_secret_mismatch");
        failed = 1;
    }

    free(pk);
    free(sk);
    free(ct);
    free(ss1);
    free(ss2);
    OQS_KEM_free(kem);

    return failed;
}

static int run_mldsa_once(const char *build_case, int iter) {
    OQS_SIG *sig = OQS_SIG_new(V37_MLDSA_ALG);
    if (sig == NULL) {
        V37_FAIL_POINT(build_case, "mldsa_valid_and_negative", iter, "OQS_SIG_new");
        return 1;
    }

    const size_t mlen = 96;

    uint8_t *pk = xmalloc(sig->length_public_key);
    uint8_t *sk = xmalloc(sig->length_secret_key);
    uint8_t *msg = xmalloc(mlen);
    uint8_t *sigbuf = xmalloc(sig->length_signature);
    size_t siglen = 0;

    fill_message(msg, mlen, iter, 0x37);

    int failed = 0;

    if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "mldsa_valid_and_negative", iter, "OQS_SIG_keypair");
        failed = 1;
    }

    if (!failed && OQS_SIG_sign(sig, sigbuf, &siglen, msg, mlen, sk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "mldsa_valid_and_negative", iter, "OQS_SIG_sign");
        failed = 1;
    }

    if (!failed && siglen > sig->length_signature) {
        V37_FAIL_POINT(build_case, "mldsa_valid_and_negative", iter, "siglen_too_large");
        failed = 1;
    }

    if (!failed && OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "mldsa_valid_and_negative", iter, "OQS_SIG_verify_valid");
        failed = 1;
    }

    if (!failed) {
        msg[0] ^= 0x01;
        if (OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) == OQS_SUCCESS) {
            V37_FAIL_POINT(build_case, "mldsa_valid_and_negative", iter, "modified_message_accepted");
            failed = 1;
        }
        msg[0] ^= 0x01;
    }

    if (!failed && siglen > 0) {
        sigbuf[0] ^= 0x01;
        if (OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) == OQS_SUCCESS) {
            V37_FAIL_POINT(build_case, "mldsa_valid_and_negative", iter, "modified_signature_accepted");
            failed = 1;
        }
        sigbuf[0] ^= 0x01;
    }

    free(pk);
    free(sk);
    free(msg);
    free(sigbuf);
    OQS_SIG_free(sig);

    return failed;
}

static int run_combined_once(const char *build_case, int iter) {
    OQS_KEM *kem = OQS_KEM_new(V37_MLKEM_ALG);
    OQS_SIG *sig = OQS_SIG_new(V37_MLDSA_ALG);

    if (kem == NULL || sig == NULL) {
        V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "OQS_new");
        if (kem != NULL) OQS_KEM_free(kem);
        if (sig != NULL) OQS_SIG_free(sig);
        return 1;
    }

    uint8_t *kem_pk = xmalloc(kem->length_public_key);
    uint8_t *kem_sk = xmalloc(kem->length_secret_key);
    uint8_t *ct = xmalloc(kem->length_ciphertext);
    uint8_t *ss1 = xmalloc(kem->length_shared_secret);
    uint8_t *ss2 = xmalloc(kem->length_shared_secret);

    uint8_t *sig_pk = xmalloc(sig->length_public_key);
    uint8_t *sig_sk = xmalloc(sig->length_secret_key);
    uint8_t *sigbuf = xmalloc(sig->length_signature);
    size_t siglen = 0;

    size_t transcript_len =
        kem->length_public_key +
        kem->length_ciphertext +
        kem->length_shared_secret;

    uint8_t *transcript = xmalloc(transcript_len);

    int failed = 0;

    if (OQS_KEM_keypair(kem, kem_pk, kem_sk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "OQS_KEM_keypair");
        failed = 1;
    }

    if (!failed && OQS_KEM_encaps(kem, ct, ss1, kem_pk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "OQS_KEM_encaps");
        failed = 1;
    }

    if (!failed && OQS_KEM_decaps(kem, ss2, ct, kem_sk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "OQS_KEM_decaps");
        failed = 1;
    }

    if (!failed && memcmp(ss1, ss2, kem->length_shared_secret) != 0) {
        V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "shared_secret_mismatch");
        failed = 1;
    }

    if (!failed) {
        size_t off = 0;
        memcpy(transcript + off, kem_pk, kem->length_public_key);
        off += kem->length_public_key;
        memcpy(transcript + off, ct, kem->length_ciphertext);
        off += kem->length_ciphertext;
        memcpy(transcript + off, ss1, kem->length_shared_secret);
    }

    if (!failed && OQS_SIG_keypair(sig, sig_pk, sig_sk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "OQS_SIG_keypair");
        failed = 1;
    }

    if (!failed && OQS_SIG_sign(sig, sigbuf, &siglen, transcript, transcript_len, sig_sk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "OQS_SIG_sign");
        failed = 1;
    }

    if (!failed && OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) != OQS_SUCCESS) {
        V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "OQS_SIG_verify_valid");
        failed = 1;
    }

    if (!failed) {
        transcript[0] ^= 0x01;
        if (OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) == OQS_SUCCESS) {
            V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "modified_transcript_accepted");
            failed = 1;
        }
        transcript[0] ^= 0x01;
    }

    if (!failed && siglen > 0) {
        sigbuf[0] ^= 0x01;
        if (OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) == OQS_SUCCESS) {
            V37_FAIL_POINT(build_case, "combined_mlkem_mldsa_sequence", iter, "modified_signature_accepted");
            failed = 1;
        }
        sigbuf[0] ^= 0x01;
    }

    free(kem_pk);
    free(kem_sk);
    free(ct);
    free(ss1);
    free(ss2);
    free(sig_pk);
    free(sig_sk);
    free(sigbuf);
    free(transcript);

    OQS_SIG_free(sig);
    OQS_KEM_free(kem);

    return failed;
}

static int run_component(const char *build_case, const char *component, int iterations) {
    int failed = 0;

    for (int i = 0; i < iterations; i++) {
        int one_failed = 0;

        if (strcmp(component, "mlkem_valid_flow") == 0) {
            one_failed = run_mlkem_once(build_case, i);
        } else if (strcmp(component, "mldsa_valid_and_negative") == 0) {
            one_failed = run_mldsa_once(build_case, i);
        } else if (strcmp(component, "combined_mlkem_mldsa_sequence") == 0) {
            one_failed = run_combined_once(build_case, i);
        } else {
            V37_FAIL_POINT(build_case, component, i, "unknown_component");
            one_failed = 1;
        }

        failed += one_failed;
    }

    int passed = iterations - failed;
    if (passed < 0) {
        passed = 0;
    }

    printf(
        "V37_CASE,%s,%s,%d,%d,%d,%s,%s\n",
        build_case,
        component,
        iterations,
        passed,
        failed,
        failed == 0 ? "PASS" : "FAIL",
        "core correctness"
    );

    return failed;
}

int main(int argc, char **argv) {
    const char *build_case = "unknown_build_case";
    int iterations = 20;

    if (argc >= 2) {
        build_case = argv[1];
    }

    if (argc >= 3) {
        iterations = atoi(argv[2]);
    }

    if (iterations <= 0) {
        fprintf(stderr, "usage: %s [build_case] [iterations]\n", argv[0]);
        return 2;
    }

    OQS_randombytes_custom_algorithm(v37_randombytes);

    const size_t mlkem_ws = v37_mlkem_workspace_need();
    const size_t mldsa_ws = v37_mldsa_workspace_need();
    const size_t combined_ws = mlkem_ws + mldsa_ws;

    uint8_t *mlkem_workspace = xaligned_malloc(64, mlkem_ws);
    uint8_t *mldsa_workspace = xaligned_malloc(64, mldsa_ws);

    memset(mlkem_workspace, 0xA5, mlkem_ws);
    memset(mldsa_workspace, 0x5A, mldsa_ws);

    if (v37_mlkem_workspace_set(mlkem_workspace) != 0) {
        V37_FAIL_POINT(build_case, "workspace_setup", -1, "v37_mlkem_workspace_set");
        free(mlkem_workspace);
        free(mldsa_workspace);
        return 1;
    }

    if (v37_mldsa_workspace_set(mldsa_workspace) != 0) {
        V37_FAIL_POINT(build_case, "workspace_setup", -1, "v37_mldsa_workspace_set");
        free(mlkem_workspace);
        free(mldsa_workspace);
        return 1;
    }

    printf("V37_CONFIG,%s,ITERATIONS,%d\n", build_case, iterations);
    printf("V37_WORKSPACE,%s,ML-KEM,%zu\n", build_case, mlkem_ws);
    printf("V37_WORKSPACE,%s,ML-DSA,%zu\n", build_case, mldsa_ws);
    printf("V37_WORKSPACE,%s,COMBINED,%zu\n", build_case, combined_ws);

    int failed_rows = 0;

    failed_rows += run_component(build_case, "mlkem_valid_flow", iterations) != 0;
    failed_rows += run_component(build_case, "mldsa_valid_and_negative", iterations) != 0;
    failed_rows += run_component(build_case, "combined_mlkem_mldsa_sequence", iterations) != 0;

    const int total_rows = 3;
    const int pass_rows = total_rows - failed_rows;

    printf(
        "V37_SUMMARY,%s,%d,%d,%d,%s\n",
        build_case,
        total_rows,
        pass_rows,
        failed_rows,
        failed_rows == 0 ? "PASS" : "FAIL"
    );

    free(mlkem_workspace);
    free(mldsa_workspace);

    return failed_rows == 0 ? 0 : 1;
}
