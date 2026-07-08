#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "v36_workspace_setup.generated.h"

#ifdef OQS_KEM_alg_ml_kem_768
#define V36_MLKEM_ALG OQS_KEM_alg_ml_kem_768
#else
#define V36_MLKEM_ALG "ML-KEM-768"
#endif

#ifdef OQS_SIG_alg_ml_dsa_44
#define V36_MLDSA_ALG OQS_SIG_alg_ml_dsa_44
#else
#define V36_MLDSA_ALG "ML-DSA-44"
#endif

#define V36_GUARD_SIZE 64

enum v36_mode {
    V36_MODE_MLKEM = 1,
    V36_MODE_MLDSA = 2,
    V36_MODE_COMBINED = 3
};

static pthread_mutex_t v36_rng_lock = PTHREAD_MUTEX_INITIALIZER;
static uint64_t v36_rng_state = 0x36b00d1234567890ULL;

static uint64_t v36_xorshift64star_locked(void) {
    uint64_t x = v36_rng_state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    v36_rng_state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

static void v36_randombytes(uint8_t *out, size_t outlen) {
    pthread_mutex_lock(&v36_rng_lock);

    size_t i = 0;
    while (i < outlen) {
        uint64_t r = v36_xorshift64star_locked();
        for (size_t j = 0; j < 8 && i < outlen; j++, i++) {
            out[i] = (uint8_t)(r >> (8 * j));
        }
    }

    pthread_mutex_unlock(&v36_rng_lock);
}

typedef struct {
    uint8_t *raw;
    uint8_t *workspace;
    size_t workspace_size;
    size_t raw_size;
    uint8_t tag;
} v36_guarded_workspace;

typedef struct {
    const char *case_name;
    int thread_index;
    int iterations;
    enum v36_mode mode;
    int repeated_setter;
    int failures;
    int canary_failures;
} v36_thread_arg;

static uint8_t guard_left_byte(uint8_t tag, size_t i) {
    return (uint8_t)(0xA0u ^ tag ^ (uint8_t)i);
}

static uint8_t guard_right_byte(uint8_t tag, size_t i) {
    return (uint8_t)(0x5Au ^ tag ^ (uint8_t)(i * 3u));
}

static void *xmalloc(size_t n) {
    void *p = malloc(n);
    if (p == NULL) {
        fprintf(stderr, "malloc failed for %zu bytes\n", n);
        exit(2);
    }
    return p;
}

static void guarded_workspace_init(v36_guarded_workspace *gw, size_t workspace_size, uint8_t tag) {
    memset(gw, 0, sizeof(*gw));

    gw->workspace_size = workspace_size;
    gw->raw_size = V36_GUARD_SIZE + workspace_size + V36_GUARD_SIZE;
    gw->tag = tag;

    if (posix_memalign((void **)&gw->raw, 64, gw->raw_size) != 0 || gw->raw == NULL) {
        fprintf(stderr, "posix_memalign failed for %zu bytes\n", gw->raw_size);
        exit(2);
    }

    gw->workspace = gw->raw + V36_GUARD_SIZE;

    for (size_t i = 0; i < V36_GUARD_SIZE; i++) {
        gw->raw[i] = guard_left_byte(tag, i);
        gw->raw[V36_GUARD_SIZE + workspace_size + i] = guard_right_byte(tag, i);
    }

    memset(gw->workspace, 0xC3, workspace_size);
}

static int guarded_workspace_check(const v36_guarded_workspace *gw) {
    int failed = 0;

    for (size_t i = 0; i < V36_GUARD_SIZE; i++) {
        if (gw->raw[i] != guard_left_byte(gw->tag, i)) {
            failed = 1;
        }
        if (gw->raw[V36_GUARD_SIZE + gw->workspace_size + i] != guard_right_byte(gw->tag, i)) {
            failed = 1;
        }
    }

    return failed;
}

static void guarded_workspace_free(v36_guarded_workspace *gw) {
    free(gw->raw);
    memset(gw, 0, sizeof(*gw));
}

static void fill_message(uint8_t *m, size_t mlen, int iter, int tid, uint8_t domain) {
    for (size_t i = 0; i < mlen; i++) {
        m[i] = (uint8_t)(domain ^ (uint8_t)i ^ (uint8_t)(iter * 131) ^ (uint8_t)(tid * 17));
    }
}

#define V36_FAIL_POINT(case_name, thread_id, iter, point) \
    fprintf(stderr, "V36_FAIL_POINT,%s,thread=%d,iter=%d,%s\n", (case_name), (thread_id), (iter), (point))

static int set_mlkem_workspace(v36_guarded_workspace *gw, const char *case_name, int tid, int iter) {
    if (v36_mlkem_workspace_set(gw->workspace) != 0) {
        V36_FAIL_POINT(case_name, tid, iter, "mlkem_workspace_set");
        return -1;
    }
    return 0;
}

static int set_mldsa_workspace(v36_guarded_workspace *gw, const char *case_name, int tid, int iter) {
    if (v36_mldsa_workspace_set(gw->workspace) != 0) {
        V36_FAIL_POINT(case_name, tid, iter, "mldsa_workspace_set");
        return -1;
    }
    return 0;
}

static int run_mlkem_once(const char *case_name, int tid, int iter) {
    OQS_KEM *kem = OQS_KEM_new(V36_MLKEM_ALG);
    if (kem == NULL) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_KEM_new");
        return 1;
    }

    uint8_t *pk = xmalloc(kem->length_public_key);
    uint8_t *sk = xmalloc(kem->length_secret_key);
    uint8_t *ct = xmalloc(kem->length_ciphertext);
    uint8_t *ss1 = xmalloc(kem->length_shared_secret);
    uint8_t *ss2 = xmalloc(kem->length_shared_secret);

    int failed = 0;

    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_KEM_keypair");
        failed = 1;
    }

    if (!failed && OQS_KEM_encaps(kem, ct, ss1, pk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_KEM_encaps");
        failed = 1;
    }

    if (!failed && OQS_KEM_decaps(kem, ss2, ct, sk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_KEM_decaps");
        failed = 1;
    }

    if (!failed && memcmp(ss1, ss2, kem->length_shared_secret) != 0) {
        V36_FAIL_POINT(case_name, tid, iter, "shared_secret_mismatch");
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

static int run_mldsa_once(const char *case_name, int tid, int iter) {
    OQS_SIG *sig = OQS_SIG_new(V36_MLDSA_ALG);
    if (sig == NULL) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_SIG_new");
        return 1;
    }

    const size_t mlen = 96;
    uint8_t *pk = xmalloc(sig->length_public_key);
    uint8_t *sk = xmalloc(sig->length_secret_key);
    uint8_t *msg = xmalloc(mlen);
    uint8_t *sigbuf = xmalloc(sig->length_signature);
    size_t siglen = 0;

    fill_message(msg, mlen, iter, tid, 0x44);

    int failed = 0;

    if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_SIG_keypair");
        failed = 1;
    }

    if (!failed && OQS_SIG_sign(sig, sigbuf, &siglen, msg, mlen, sk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_SIG_sign");
        failed = 1;
    }

    if (!failed && siglen > sig->length_signature) {
        V36_FAIL_POINT(case_name, tid, iter, "siglen_too_large");
        failed = 1;
    }

    if (!failed && OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_SIG_verify_valid");
        failed = 1;
    }

    if (!failed) {
        msg[0] ^= 0x01;
        if (OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) == OQS_SUCCESS) {
            V36_FAIL_POINT(case_name, tid, iter, "modified_message_accepted");
            failed = 1;
        }
        msg[0] ^= 0x01;
    }

    if (!failed && siglen > 0) {
        sigbuf[0] ^= 0x01;
        if (OQS_SIG_verify(sig, msg, mlen, sigbuf, siglen, pk) == OQS_SUCCESS) {
            V36_FAIL_POINT(case_name, tid, iter, "modified_signature_accepted");
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

static int run_combined_once(const char *case_name, int tid, int iter) {
    OQS_KEM *kem = OQS_KEM_new(V36_MLKEM_ALG);
    OQS_SIG *sig = OQS_SIG_new(V36_MLDSA_ALG);

    if (kem == NULL || sig == NULL) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_new");
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
        V36_FAIL_POINT(case_name, tid, iter, "OQS_KEM_keypair");
        failed = 1;
    }

    if (!failed && OQS_KEM_encaps(kem, ct, ss1, kem_pk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_KEM_encaps");
        failed = 1;
    }

    if (!failed && OQS_KEM_decaps(kem, ss2, ct, kem_sk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_KEM_decaps");
        failed = 1;
    }

    if (!failed && memcmp(ss1, ss2, kem->length_shared_secret) != 0) {
        V36_FAIL_POINT(case_name, tid, iter, "shared_secret_mismatch");
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
        V36_FAIL_POINT(case_name, tid, iter, "OQS_SIG_keypair");
        failed = 1;
    }

    if (!failed && OQS_SIG_sign(sig, sigbuf, &siglen, transcript, transcript_len, sig_sk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_SIG_sign");
        failed = 1;
    }

    if (!failed && OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) != OQS_SUCCESS) {
        V36_FAIL_POINT(case_name, tid, iter, "OQS_SIG_verify_valid");
        failed = 1;
    }

    if (!failed) {
        transcript[0] ^= 0x01;
        if (OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) == OQS_SUCCESS) {
            V36_FAIL_POINT(case_name, tid, iter, "modified_transcript_accepted");
            failed = 1;
        }
        transcript[0] ^= 0x01;
    }

    if (!failed && siglen > 0) {
        sigbuf[0] ^= 0x01;
        if (OQS_SIG_verify(sig, transcript, transcript_len, sigbuf, siglen, sig_pk) == OQS_SUCCESS) {
            V36_FAIL_POINT(case_name, tid, iter, "modified_signature_accepted");
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

static int mode_needs_mlkem(enum v36_mode mode) {
    return mode == V36_MODE_MLKEM || mode == V36_MODE_COMBINED;
}

static int mode_needs_mldsa(enum v36_mode mode) {
    return mode == V36_MODE_MLDSA || mode == V36_MODE_COMBINED;
}

static void *thread_main(void *opaque) {
    v36_thread_arg *arg = (v36_thread_arg *)opaque;

    v36_guarded_workspace mlkem_ws;
    v36_guarded_workspace mldsa_ws;

    int has_mlkem = mode_needs_mlkem(arg->mode);
    int has_mldsa = mode_needs_mldsa(arg->mode);

    memset(&mlkem_ws, 0, sizeof(mlkem_ws));
    memset(&mldsa_ws, 0, sizeof(mldsa_ws));

    if (has_mlkem) {
        guarded_workspace_init(
            &mlkem_ws,
            v36_mlkem_workspace_need(),
            (uint8_t)(0x10u + (uint8_t)arg->thread_index)
        );

        if (set_mlkem_workspace(&mlkem_ws, arg->case_name, arg->thread_index, -1) != 0) {
            arg->failures++;
        }
    }

    if (has_mldsa) {
        guarded_workspace_init(
            &mldsa_ws,
            v36_mldsa_workspace_need(),
            (uint8_t)(0x80u + (uint8_t)arg->thread_index)
        );

        if (set_mldsa_workspace(&mldsa_ws, arg->case_name, arg->thread_index, -1) != 0) {
            arg->failures++;
        }
    }

    for (int i = 0; i < arg->iterations; i++) {
        if (arg->repeated_setter) {
            if (has_mlkem && set_mlkem_workspace(&mlkem_ws, arg->case_name, arg->thread_index, i) != 0) {
                arg->failures++;
                continue;
            }
            if (has_mldsa && set_mldsa_workspace(&mldsa_ws, arg->case_name, arg->thread_index, i) != 0) {
                arg->failures++;
                continue;
            }
        }

        int failed = 0;

        if (arg->mode == V36_MODE_MLKEM) {
            failed = run_mlkem_once(arg->case_name, arg->thread_index, i);
        } else if (arg->mode == V36_MODE_MLDSA) {
            failed = run_mldsa_once(arg->case_name, arg->thread_index, i);
        } else if (arg->mode == V36_MODE_COMBINED) {
            failed = run_combined_once(arg->case_name, arg->thread_index, i);
        } else {
            V36_FAIL_POINT(arg->case_name, arg->thread_index, i, "unknown_mode");
            failed = 1;
        }

        if (failed) {
            arg->failures++;
        }

        if (has_mlkem && guarded_workspace_check(&mlkem_ws) != 0) {
            V36_FAIL_POINT(arg->case_name, arg->thread_index, i, "mlkem_workspace_canary_corruption");
            arg->canary_failures++;
        }

        if (has_mldsa && guarded_workspace_check(&mldsa_ws) != 0) {
            V36_FAIL_POINT(arg->case_name, arg->thread_index, i, "mldsa_workspace_canary_corruption");
            arg->canary_failures++;
        }
    }

    if (has_mlkem) {
        guarded_workspace_free(&mlkem_ws);
    }

    if (has_mldsa) {
        guarded_workspace_free(&mldsa_ws);
    }

    return NULL;
}

static int run_parallel_case(
    const char *case_name,
    enum v36_mode mode,
    int threads,
    int iterations_per_thread,
    int repeated_setter
) {
    pthread_t *tids = (pthread_t *)xmalloc(sizeof(pthread_t) * (size_t)threads);
    v36_thread_arg *args = (v36_thread_arg *)xmalloc(sizeof(v36_thread_arg) * (size_t)threads);

    for (int i = 0; i < threads; i++) {
        args[i].case_name = case_name;
        args[i].thread_index = i;
        args[i].iterations = iterations_per_thread;
        args[i].mode = mode;
        args[i].repeated_setter = repeated_setter;
        args[i].failures = 0;
        args[i].canary_failures = 0;

        if (pthread_create(&tids[i], NULL, thread_main, &args[i]) != 0) {
            fprintf(stderr, "V36_FAIL_POINT,%s,thread=%d,iter=-1,pthread_create\n", case_name, i);
            args[i].failures++;
        }
    }

    int worker_failures = 0;
    int canary_failures = 0;

    for (int i = 0; i < threads; i++) {
        pthread_join(tids[i], NULL);
        worker_failures += args[i].failures;
        canary_failures += args[i].canary_failures;
    }

    int total_ops = threads * iterations_per_thread;
    int failed = worker_failures + canary_failures;
    int passed = total_ops - worker_failures;

    if (passed < 0) {
        passed = 0;
    }

    const char *status = failed == 0 ? "PASS" : "FAIL";

    printf(
        "V36_CASE,%s,%d,%d,%d,%d,%d,%d,%s,%s\n",
        case_name,
        threads,
        iterations_per_thread,
        total_ops,
        passed,
        worker_failures,
        canary_failures,
        status,
        repeated_setter ? "repeated setter stress" : "thread-local workspace"
    );

    free(tids);
    free(args);

    return failed;
}

int main(int argc, char **argv) {
    int threads = 8;
    int iterations_per_thread = 100;

    if (argc >= 2) {
        threads = atoi(argv[1]);
    }

    if (argc >= 3) {
        iterations_per_thread = atoi(argv[2]);
    }

    if (threads <= 0 || iterations_per_thread <= 0) {
        fprintf(stderr, "usage: %s [threads] [iterations_per_thread]\n", argv[0]);
        return 2;
    }

    OQS_randombytes_custom_algorithm(v36_randombytes);

    const size_t mlkem_ws = v36_mlkem_workspace_need();
    const size_t mldsa_ws = v36_mldsa_workspace_need();
    const size_t combined_ws = mlkem_ws + mldsa_ws;

    printf("V36_CONFIG,THREADS,%d\n", threads);
    printf("V36_CONFIG,ITERATIONS_PER_THREAD,%d\n", iterations_per_thread);
    printf("V36_WORKSPACE,ML-KEM,%zu\n", mlkem_ws);
    printf("V36_WORKSPACE,ML-DSA,%zu\n", mldsa_ws);
    printf("V36_WORKSPACE,COMBINED,%zu\n", combined_ws);

    int failed_rows = 0;

    failed_rows += run_parallel_case(
        "single_thread_control",
        V36_MODE_COMBINED,
        1,
        iterations_per_thread,
        0
    ) != 0;

    failed_rows += run_parallel_case(
        "multi_thread_mlkem",
        V36_MODE_MLKEM,
        threads,
        iterations_per_thread,
        0
    ) != 0;

    failed_rows += run_parallel_case(
        "multi_thread_mldsa",
        V36_MODE_MLDSA,
        threads,
        iterations_per_thread,
        0
    ) != 0;

    failed_rows += run_parallel_case(
        "multi_thread_combined",
        V36_MODE_COMBINED,
        threads,
        iterations_per_thread,
        0
    ) != 0;

    failed_rows += run_parallel_case(
        "thread_repeated_setter_stress",
        V36_MODE_COMBINED,
        threads,
        iterations_per_thread,
        1
    ) != 0;

    const int total_rows = 5;
    const int pass_rows = total_rows - failed_rows;

    printf(
        "V36_SUMMARY,%d,%d,%d,%s\n",
        total_rows,
        pass_rows,
        failed_rows,
        failed_rows == 0 ? "PASS" : "FAIL"
    );

    return failed_rows == 0 ? 0 : 1;
}
