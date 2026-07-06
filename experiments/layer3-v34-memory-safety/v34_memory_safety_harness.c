#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "v34_workspace_setup.generated.h"

#ifndef V34_USE_WORKSPACE
#define V34_USE_WORKSPACE 1
#endif

#ifdef OQS_KEM_alg_ml_kem_768
#define V34_MLKEM_ALG OQS_KEM_alg_ml_kem_768
#else
#define V34_MLKEM_ALG "ML-KEM-768"
#endif

#ifdef OQS_SIG_alg_ml_dsa_44
#define V34_MLDSA_ALG OQS_SIG_alg_ml_dsa_44
#else
#define V34_MLDSA_ALG "ML-DSA-44"
#endif

static uint64_t v34_rng_state = 0x123456789abcdef0ULL;

static uint64_t v34_xorshift64star(void) {
    uint64_t x = v34_rng_state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    v34_rng_state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

static void v34_rng_seed(uint64_t seed) {
    if (seed == 0) {
        seed = 0x123456789abcdef0ULL;
    }
    v34_rng_state = seed;
}

static void v34_randombytes(uint8_t *out, size_t outlen) {
    size_t i = 0;
    while (i < outlen) {
        uint64_t r = v34_xorshift64star();
        for (size_t j = 0; j < 8 && i < outlen; j++, i++) {
            out[i] = (uint8_t)(r >> (8 * j));
        }
    }
}

static uint8_t *g_mlkem_workspace = NULL;
static uint8_t *g_mldsa_workspace = NULL;

static void *v34_aligned_alloc_or_die(size_t alignment, size_t bytes) {
    void *ptr = NULL;
    if (bytes == 0) {
        fprintf(stderr, "workspace size is zero\n");
        exit(2);
    }

    if (posix_memalign(&ptr, alignment, bytes) != 0 || ptr == NULL) {
        fprintf(stderr, "posix_memalign failed for %zu bytes\n", bytes);
        exit(2);
    }

    memset(ptr, 0xA5, bytes);
    return ptr;
}

static int v34_setup_mlkem_workspace(void) {
#if V34_USE_WORKSPACE
    size_t need = v34_mlkem_workspace_need();
    if (need == 0) {
        fprintf(stderr, "ML-KEM workspace need is zero\n");
        return -1;
    }

    if (g_mlkem_workspace == NULL) {
        g_mlkem_workspace = (uint8_t *)v34_aligned_alloc_or_die(64, need);
    }

    if (v34_mlkem_workspace_set(g_mlkem_workspace) != 0) {
        fprintf(stderr, "ML-KEM workspace setter failed\n");
        return -1;
    }
#endif
    return 0;
}

static int v34_setup_mldsa_workspace(void) {
#if V34_USE_WORKSPACE
    size_t need = v34_mldsa_workspace_need();
    if (need == 0) {
        fprintf(stderr, "ML-DSA workspace need is zero\n");
        return -1;
    }

    if (g_mldsa_workspace == NULL) {
        g_mldsa_workspace = (uint8_t *)v34_aligned_alloc_or_die(64, need);
    }

    if (v34_mldsa_workspace_set(g_mldsa_workspace) != 0) {
        fprintf(stderr, "ML-DSA workspace setter failed\n");
        return -1;
    }
#endif
    return 0;
}

static void v34_cleanup_workspaces(void) {
    free(g_mlkem_workspace);
    free(g_mldsa_workspace);
    g_mlkem_workspace = NULL;
    g_mldsa_workspace = NULL;
}

static uint8_t *xmalloc(size_t n) {
    uint8_t *p = (uint8_t *)malloc(n);
    if (p == NULL) {
        fprintf(stderr, "malloc failed for %zu bytes\n", n);
        exit(2);
    }
    return p;
}

static void fill_message(uint8_t *m, size_t mlen, int iter, uint8_t domain) {
    for (size_t i = 0; i < mlen; i++) {
        m[i] = (uint8_t)(domain ^ (uint8_t)i ^ (uint8_t)(iter * 131));
    }
}

#define V34_FAIL_POINT(case_name, iter, point) \
    fprintf(stderr, "V34_FAIL_POINT,%s,%d,%s\n", (case_name), (iter), (point))

static void print_case_result(const char *name, int iterations, int passed, int failed) {
    const char *status = (failed == 0 && passed == iterations) ? "PASS" : "FAIL";
    printf("V34_CASE,%s,%d,%d,%d,%s\n", name, iterations, passed, failed, status);
}

static int test_mlkem_valid_flow(int iterations) {
    int passed = 0;
    int failed = 0;

    for (int i = 0; i < iterations; i++) {
        v34_rng_seed(0x100000000ULL + (uint64_t)i);

        OQS_KEM *kem = OQS_KEM_new(V34_MLKEM_ALG);
        if (kem == NULL) {
            fprintf(stderr, "OQS_KEM_new failed for %s\n", V34_MLKEM_ALG);
            failed++;
            continue;
        }

        if (v34_setup_mlkem_workspace() != 0) {
            failed++;
            OQS_KEM_free(kem);
            continue;
        }

        uint8_t *pk = xmalloc(kem->length_public_key);
        uint8_t *sk = xmalloc(kem->length_secret_key);
        uint8_t *ct = xmalloc(kem->length_ciphertext);
        uint8_t *ss1 = xmalloc(kem->length_shared_secret);
        uint8_t *ss2 = xmalloc(kem->length_shared_secret);

        int ok = 1;

        if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
            V34_FAIL_POINT("mlkem_valid_flow", i, "OQS_KEM_keypair");
            ok = 0;
        }
        if (ok && OQS_KEM_encaps(kem, ct, ss1, pk) != OQS_SUCCESS) {
            V34_FAIL_POINT("mlkem_valid_flow", i, "OQS_KEM_encaps");
            ok = 0;
        }
        if (ok && OQS_KEM_decaps(kem, ss2, ct, sk) != OQS_SUCCESS) {
            V34_FAIL_POINT("mlkem_valid_flow", i, "OQS_KEM_decaps");
            ok = 0;
        }
        if (ok && memcmp(ss1, ss2, kem->length_shared_secret) != 0) {
            V34_FAIL_POINT("mlkem_valid_flow", i, "shared_secret_mismatch");
            ok = 0;
        }

        free(pk);
        free(sk);
        free(ct);
        free(ss1);
        free(ss2);
        OQS_KEM_free(kem);

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

    print_case_result("mlkem_valid_flow", iterations, passed, failed);
    return failed;
}

static int test_mldsa_valid_and_negative(int iterations) {
    int passed = 0;
    int failed = 0;

    for (int i = 0; i < iterations; i++) {
        v34_rng_seed(0x200000000ULL + (uint64_t)i);

        OQS_SIG *sig = OQS_SIG_new(V34_MLDSA_ALG);
        if (sig == NULL) {
            fprintf(stderr, "OQS_SIG_new failed for %s\n", V34_MLDSA_ALG);
            failed++;
            continue;
        }

        if (v34_setup_mldsa_workspace() != 0) {
            failed++;
            OQS_SIG_free(sig);
            continue;
        }

        const size_t mlen = 96;
        uint8_t *pk = xmalloc(sig->length_public_key);
        uint8_t *sk = xmalloc(sig->length_secret_key);
        uint8_t *msg = xmalloc(mlen);
        uint8_t *sigbuf = xmalloc(sig->length_signature);
        size_t siglen = 0;

        fill_message(msg, mlen, i, 0x44);

        int ok = 1;

        if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
            V34_FAIL_POINT("mldsa_valid_and_negative", i, "OQS_SIG_keypair");
            ok = 0;
        }
        if (ok && OQS_SIG_sign(sig, sigbuf, &siglen, msg, mlen, sk) != OQS_SUCCESS) {
            V34_FAIL_POINT("mldsa_valid_and_negative", i, "OQS_SIG_sign");
            ok = 0;
        }
        if (ok && siglen > sig->length_signature) {
            V34_FAIL_POINT("mldsa_valid_and_negative", i, "siglen_too_large");
            ok = 0;
        }
        if (ok && OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) != OQS_SUCCESS) {
            V34_FAIL_POINT("mldsa_valid_and_negative", i, "OQS_SIG_verify_valid");
            ok = 0;
        }

        if (ok) {
            msg[0] ^= 0x01;
            if (OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) == OQS_SUCCESS) {
                V34_FAIL_POINT("mldsa_valid_and_negative", i, "modified_message_accepted");
                ok = 0;
            }
            msg[0] ^= 0x01;
        }

        if (ok && siglen > 0) {
            sigbuf[0] ^= 0x01;
            if (OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) == OQS_SUCCESS) {
                V34_FAIL_POINT("mldsa_valid_and_negative", i, "modified_signature_accepted");
                ok = 0;
            }
            sigbuf[0] ^= 0x01;
        }

        free(pk);
        free(sk);
        free(msg);
        free(sigbuf);
        OQS_SIG_free(sig);

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

    print_case_result("mldsa_valid_and_negative", iterations, passed, failed);
    return failed;
}

static int test_combined_sequence(int iterations) {
    int passed = 0;
    int failed = 0;

    for (int i = 0; i < iterations; i++) {
        v34_rng_seed(0x300000000ULL + (uint64_t)i);

        OQS_KEM *kem = OQS_KEM_new(V34_MLKEM_ALG);
        if (kem == NULL) {
            fprintf(stderr, "OQS_KEM_new failed for %s\n", V34_MLKEM_ALG);
            failed++;
            continue;
        }

        if (v34_setup_mlkem_workspace() != 0) {
            failed++;
            OQS_KEM_free(kem);
            continue;
        }

        OQS_SIG *sig = OQS_SIG_new(V34_MLDSA_ALG);
        if (sig == NULL) {
            fprintf(stderr, "OQS_SIG_new failed for %s\n", V34_MLDSA_ALG);
            failed++;
            OQS_KEM_free(kem);
            continue;
        }

        if (v34_setup_mldsa_workspace() != 0) {
            failed++;
            OQS_SIG_free(sig);
            OQS_KEM_free(kem);
            continue;
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

        int ok = 1;

        if (OQS_KEM_keypair(kem, kem_pk, kem_sk) != OQS_SUCCESS) {
            V34_FAIL_POINT("combined_mlkem_mldsa_sequence", i, "OQS_KEM_keypair");
            ok = 0;
        }
        if (ok && OQS_KEM_encaps(kem, ct, ss1, kem_pk) != OQS_SUCCESS) {
            V34_FAIL_POINT("combined_mlkem_mldsa_sequence", i, "OQS_KEM_encaps");
            ok = 0;
        }
        if (ok && OQS_KEM_decaps(kem, ss2, ct, kem_sk) != OQS_SUCCESS) {
            V34_FAIL_POINT("combined_mlkem_mldsa_sequence", i, "OQS_KEM_decaps");
            ok = 0;
        }
        if (ok && memcmp(ss1, ss2, kem->length_shared_secret) != 0) {
            V34_FAIL_POINT("combined_mlkem_mldsa_sequence", i, "shared_secret_mismatch");
            ok = 0;
        }

        if (ok) {
            size_t off = 0;
            memcpy(transcript + off, kem_pk, kem->length_public_key);
            off += kem->length_public_key;
            memcpy(transcript + off, ct, kem->length_ciphertext);
            off += kem->length_ciphertext;
            memcpy(transcript + off, ss1, kem->length_shared_secret);
        }

        if (ok && OQS_SIG_keypair(sig, sig_pk, sig_sk) != OQS_SUCCESS) {
            V34_FAIL_POINT("combined_mlkem_mldsa_sequence", i, "OQS_SIG_keypair");
            ok = 0;
        }
        if (ok && OQS_SIG_sign(sig, sigbuf, &siglen, transcript, transcript_len, sig_sk) != OQS_SUCCESS) {
            V34_FAIL_POINT("combined_mlkem_mldsa_sequence", i, "OQS_SIG_sign");
            ok = 0;
        }
        if (ok && OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) != OQS_SUCCESS) {
            V34_FAIL_POINT("combined_mlkem_mldsa_sequence", i, "OQS_SIG_verify_valid");
            ok = 0;
        }

        if (ok) {
            transcript[0] ^= 0x01;
            if (OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) == OQS_SUCCESS) {
                ok = 0;
            }
            transcript[0] ^= 0x01;
        }

        if (ok && siglen > 0) {
            sigbuf[0] ^= 0x01;
            if (OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) == OQS_SUCCESS) {
                ok = 0;
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

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

    print_case_result("combined_mlkem_mldsa_sequence", iterations, passed, failed);
    return failed;
}

int main(int argc, char **argv) {
    int iterations = 100;

    if (argc >= 2) {
        iterations = atoi(argv[1]);
    }

    if (iterations <= 0) {
        fprintf(stderr, "iterations must be positive\n");
        return 2;
    }

    atexit(v34_cleanup_workspaces);

    OQS_randombytes_custom_algorithm(v34_randombytes);

    printf("V34_WORKSPACE,ML-KEM,%zu\n", v34_mlkem_workspace_need());
    printf("V34_WORKSPACE,ML-DSA,%zu\n", v34_mldsa_workspace_need());
    printf("V34_WORKSPACE,COMBINED,%zu\n", v34_mlkem_workspace_need() + v34_mldsa_workspace_need());

    int failed = 0;
    int total_cases = 3;
    int pass_cases = 0;

    int f1 = test_mlkem_valid_flow(iterations);
    int f2 = test_mldsa_valid_and_negative(iterations);
    int f3 = test_combined_sequence(iterations);

    failed = f1 + f2 + f3;

    if (f1 == 0) pass_cases++;
    if (f2 == 0) pass_cases++;
    if (f3 == 0) pass_cases++;

    printf("V34_SUMMARY,%d,%d,%d,%s\n",
           total_cases,
           pass_cases,
           total_cases - pass_cases,
           failed == 0 ? "PASS" : "FAIL");

    return failed == 0 ? 0 : 1;
}
