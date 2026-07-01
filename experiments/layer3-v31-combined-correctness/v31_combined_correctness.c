#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <time.h>
#include <unistd.h>

#include "v31_workspace_setup.generated.h"

#ifndef OQS_KEM_alg_ml_kem_768
#define V31_MLKEM_ALG "ML-KEM-768"
#else
#define V31_MLKEM_ALG OQS_KEM_alg_ml_kem_768
#endif

#ifndef OQS_SIG_alg_ml_dsa_44
#define V31_MLDSA_ALG "ML-DSA-44"
#else
#define V31_MLDSA_ALG OQS_SIG_alg_ml_dsa_44
#endif

typedef struct {
    const char *name;
    uint64_t iterations;
    uint64_t passed;
    uint64_t failed;
    double mean_us;
} v31_result;

static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ((uint64_t) ts.tv_sec * 1000000000ULL) + (uint64_t) ts.tv_nsec;
}

static void *xcalloc(size_t n, size_t s) {
    void *p = calloc(n, s);
    if (p == NULL) {
        fprintf(stderr, "allocation failed: %zu x %zu\n", n, s);
        exit(2);
    }
    return p;
}

static void v31_randombytes(uint8_t *out, size_t out_len) {
    size_t off = 0;

    while (off < out_len) {
        ssize_t got = getrandom(out + off, out_len - off, 0);

        if (got > 0) {
            off += (size_t) got;
            continue;
        }

        if (got < 0 && errno == EINTR) {
            continue;
        }

        break;
    }

    if (off == out_len) {
        return;
    }

    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0) {
        perror("open /dev/urandom");
        abort();
    }

    while (off < out_len) {
        ssize_t got = read(fd, out + off, out_len - off);

        if (got > 0) {
            off += (size_t) got;
            continue;
        }

        if (got < 0 && errno == EINTR) {
            continue;
        }

        perror("read /dev/urandom");
        close(fd);
        abort();
    }

    close(fd);
}

static void fill_message(uint8_t *msg, size_t len, uint64_t iter) {
    for (size_t i = 0; i < len; i++) {
        msg[i] = (uint8_t) ((i * 131u + iter * 17u + 0x42u) & 0xffu);
    }
}

static void write_result(FILE *csv, const v31_result *r) {
    const char *status = (r->failed == 0) ? "PASS" : "FAIL";

    fprintf(
        csv,
        "%s,%llu,%llu,%llu,%.3f,%s\n",
        r->name,
        (unsigned long long) r->iterations,
        (unsigned long long) r->passed,
        (unsigned long long) r->failed,
        r->mean_us,
        status
    );

    printf(
        "%-36s iterations=%llu passed=%llu failed=%llu mean_us=%.3f status=%s\n",
        r->name,
        (unsigned long long) r->iterations,
        (unsigned long long) r->passed,
        (unsigned long long) r->failed,
        r->mean_us,
        status
    );
}

static v31_result run_mlkem_valid_flow(OQS_KEM *kem, uint64_t iterations) {
    v31_result r = {
        .name = "mlkem_valid_flow",
        .iterations = iterations,
        .passed = 0,
        .failed = 0,
        .mean_us = 0.0,
    };

    uint8_t *pk = xcalloc(kem->length_public_key, 1);
    uint8_t *sk = xcalloc(kem->length_secret_key, 1);
    uint8_t *ct = xcalloc(kem->length_ciphertext, 1);
    uint8_t *ss_enc = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ss_dec = xcalloc(kem->length_shared_secret, 1);

    uint64_t start = now_ns();

    for (uint64_t i = 0; i < iterations; i++) {
        int ok = 1;

        if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_KEM_encaps(kem, ct, ss_enc, pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_KEM_decaps(kem, ss_dec, ct, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && memcmp(ss_enc, ss_dec, kem->length_shared_secret) != 0) {
            ok = 0;
        }

        if (ok) {
            r.passed++;
        } else {
            r.failed++;
        }
    }

    uint64_t end = now_ns();
    r.mean_us = ((double) (end - start) / 1000.0) / (double) iterations;

    free(pk);
    free(sk);
    free(ct);
    free(ss_enc);
    free(ss_dec);

    return r;
}

static v31_result run_mldsa_valid_and_negative(OQS_SIG *sig, uint64_t iterations) {
    v31_result r = {
        .name = "mldsa_valid_and_negative",
        .iterations = iterations,
        .passed = 0,
        .failed = 0,
        .mean_us = 0.0,
    };

    const size_t msg_len = 96;

    uint8_t *pk = xcalloc(sig->length_public_key, 1);
    uint8_t *sk = xcalloc(sig->length_secret_key, 1);
    uint8_t *signature = xcalloc(sig->length_signature, 1);
    uint8_t *bad_signature = xcalloc(sig->length_signature, 1);
    uint8_t *msg = xcalloc(msg_len, 1);
    uint8_t *bad_msg = xcalloc(msg_len, 1);

    uint64_t start = now_ns();

    for (uint64_t i = 0; i < iterations; i++) {
        int ok = 1;
        size_t sig_len = 0;

        fill_message(msg, msg_len, i);

        if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_SIG_sign(sig, signature, &sig_len, msg, msg_len, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_SIG_verify(sig, msg, msg_len, signature, sig_len, pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok) {
            memcpy(bad_msg, msg, msg_len);
            bad_msg[0] ^= 0x01;

            if (OQS_SIG_verify(sig, bad_msg, msg_len, signature, sig_len, pk) == OQS_SUCCESS) {
                ok = 0;
            }
        }

        if (ok) {
            memcpy(bad_signature, signature, sig_len);

            if (sig_len > 0) {
                bad_signature[0] ^= 0x01;
            }

            if (OQS_SIG_verify(sig, msg, msg_len, bad_signature, sig_len, pk) == OQS_SUCCESS) {
                ok = 0;
            }
        }

        if (ok) {
            r.passed++;
        } else {
            r.failed++;
        }
    }

    uint64_t end = now_ns();
    r.mean_us = ((double) (end - start) / 1000.0) / (double) iterations;

    free(pk);
    free(sk);
    free(signature);
    free(bad_signature);
    free(msg);
    free(bad_msg);

    return r;
}

static v31_result run_combined_sequence(OQS_KEM *kem, OQS_SIG *sig, uint64_t iterations) {
    v31_result r = {
        .name = "combined_mlkem_mldsa_sequence",
        .iterations = iterations,
        .passed = 0,
        .failed = 0,
        .mean_us = 0.0,
    };

    uint8_t *kem_pk = xcalloc(kem->length_public_key, 1);
    uint8_t *kem_sk = xcalloc(kem->length_secret_key, 1);
    uint8_t *kem_ct = xcalloc(kem->length_ciphertext, 1);
    uint8_t *ss_enc = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ss_dec = xcalloc(kem->length_shared_secret, 1);

    uint8_t *sig_pk = xcalloc(sig->length_public_key, 1);
    uint8_t *sig_sk = xcalloc(sig->length_secret_key, 1);
    uint8_t *signature = xcalloc(sig->length_signature, 1);

    size_t transcript_len =
        kem->length_public_key +
        kem->length_ciphertext +
        kem->length_shared_secret;

    uint8_t *transcript = xcalloc(transcript_len, 1);

    uint64_t start = now_ns();

    for (uint64_t i = 0; i < iterations; i++) {
        int ok = 1;
        size_t sig_len = 0;

        if (OQS_KEM_keypair(kem, kem_pk, kem_sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_KEM_encaps(kem, kem_ct, ss_enc, kem_pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_KEM_decaps(kem, ss_dec, kem_ct, kem_sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && memcmp(ss_enc, ss_dec, kem->length_shared_secret) != 0) {
            ok = 0;
        }

        if (ok && OQS_SIG_keypair(sig, sig_pk, sig_sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok) {
            size_t off = 0;

            memcpy(transcript + off, kem_pk, kem->length_public_key);
            off += kem->length_public_key;

            memcpy(transcript + off, kem_ct, kem->length_ciphertext);
            off += kem->length_ciphertext;

            memcpy(transcript + off, ss_enc, kem->length_shared_secret);
        }

        if (ok && OQS_SIG_sign(sig, signature, &sig_len, transcript, transcript_len, sig_sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_SIG_verify(sig, transcript, transcript_len, signature, sig_len, sig_pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok) {
            r.passed++;
        } else {
            r.failed++;
        }
    }

    uint64_t end = now_ns();
    r.mean_us = ((double) (end - start) / 1000.0) / (double) iterations;

    free(kem_pk);
    free(kem_sk);
    free(kem_ct);
    free(ss_enc);
    free(ss_dec);

    free(sig_pk);
    free(sig_sk);
    free(signature);
    free(transcript);

    return r;
}

int main(int argc, char **argv) {
    OQS_randombytes_custom_algorithm(v31_randombytes);

    uint64_t iterations = 1000;

    if (argc >= 2) {
        iterations = strtoull(argv[1], NULL, 10);
        if (iterations == 0) {
            iterations = 1000;
        }
    }

    const char *csv_path = "layer3-results/v31_combined_correctness.csv";
    const char *workspace_csv_path = "layer3-results/v31_combined_workspace.csv";

    if (argc >= 3) {
        csv_path = argv[2];
    }

    if (argc >= 4) {
        workspace_csv_path = argv[3];
    }

    size_t mlkem_ws_bytes = v31_mlkem_workspace_need();
    size_t mldsa_ws_bytes = v31_mldsa_workspace_need();

    if (mlkem_ws_bytes == 0) {
        fprintf(stderr, "ML-KEM v29 lifecycle workspace symbol not found or returned zero\n");
        return 2;
    }

    if (mldsa_ws_bytes == 0) {
        fprintf(stderr, "ML-DSA v24 lifecycle workspace symbol not found or returned zero\n");
        return 2;
    }

    void *mlkem_ws = NULL;
    void *mldsa_ws = NULL;

    if (posix_memalign(&mlkem_ws, 64, mlkem_ws_bytes) != 0) {
        fprintf(stderr, "failed to allocate aligned ML-KEM workspace\n");
        return 2;
    }

    if (posix_memalign(&mldsa_ws, 64, mldsa_ws_bytes) != 0) {
        fprintf(stderr, "failed to allocate aligned ML-DSA workspace\n");
        free(mlkem_ws);
        return 2;
    }

    memset(mlkem_ws, 0, mlkem_ws_bytes);
    memset(mldsa_ws, 0, mldsa_ws_bytes);

    if (v31_mlkem_workspace_set(mlkem_ws, mlkem_ws_bytes) != 0) {
        fprintf(stderr, "failed to set ML-KEM lifecycle workspace\n");
        free(mlkem_ws);
        free(mldsa_ws);
        return 2;
    }

    if (v31_mldsa_workspace_set(mldsa_ws, mldsa_ws_bytes) != 0) {
        fprintf(stderr, "failed to set ML-DSA lifecycle workspace\n");
        free(mlkem_ws);
        free(mldsa_ws);
        return 2;
    }

    FILE *wcsv = fopen(workspace_csv_path, "w");
    if (wcsv == NULL) {
        perror("fopen workspace csv");
        free(mlkem_ws);
        free(mldsa_ws);
        return 2;
    }

    fprintf(wcsv, "scheme,workspace_kind,bytes\n");
    fprintf(wcsv, "ML-KEM-768,v29_lifecycle_workspace,%zu\n", mlkem_ws_bytes);
    fprintf(wcsv, "ML-DSA-44,v24_lifecycle_workspace,%zu\n", mldsa_ws_bytes);
    fprintf(wcsv, "Combined,mlkem_plus_mldsa_lifecycle,%zu\n", mlkem_ws_bytes + mldsa_ws_bytes);
    fclose(wcsv);

    printf("v31 workspace setup\n");
    printf("ML-KEM workspace bytes: %zu\n", mlkem_ws_bytes);
    printf("ML-DSA workspace bytes: %zu\n", mldsa_ws_bytes);
    printf("Combined workspace bytes: %zu\n", mlkem_ws_bytes + mldsa_ws_bytes);
    printf("\n");

    OQS_KEM *kem = OQS_KEM_new(V31_MLKEM_ALG);
    if (kem == NULL) {
        fprintf(stderr, "OQS_KEM_new failed for %s\n", V31_MLKEM_ALG);
        free(mlkem_ws);
        free(mldsa_ws);
        return 2;
    }

    OQS_SIG *sig = OQS_SIG_new(V31_MLDSA_ALG);
    if (sig == NULL) {
        fprintf(stderr, "OQS_SIG_new failed for %s\n", V31_MLDSA_ALG);
        OQS_KEM_free(kem);
        free(mlkem_ws);
        free(mldsa_ws);
        return 2;
    }

    /*
     * Refresh workspace pointers after OQS_KEM_new/OQS_SIG_new.
     * Some builds perform runtime dispatch setup during object creation;
     * setting again here makes the active implementation workspace pointers explicit.
     */
    if (v31_mlkem_workspace_set(mlkem_ws, mlkem_ws_bytes) != 0) {
        fprintf(stderr, "failed to refresh ML-KEM lifecycle workspace\n");
        OQS_SIG_free(sig);
        OQS_KEM_free(kem);
        free(mlkem_ws);
        free(mldsa_ws);
        return 2;
    }

    if (v31_mldsa_workspace_set(mldsa_ws, mldsa_ws_bytes) != 0) {
        fprintf(stderr, "failed to refresh ML-DSA lifecycle workspace\n");
        OQS_SIG_free(sig);
        OQS_KEM_free(kem);
        free(mlkem_ws);
        free(mldsa_ws);
        return 2;
    }

    FILE *csv = fopen(csv_path, "w");
    if (csv == NULL) {
        perror("fopen correctness csv");
        OQS_SIG_free(sig);
        OQS_KEM_free(kem);
        free(mlkem_ws);
        free(mldsa_ws);
        return 2;
    }

    fprintf(csv, "test,iterations,passed,failed,mean_us,status\n");

    v31_result mlkem = run_mlkem_valid_flow(kem, iterations);
    write_result(csv, &mlkem);

    v31_result mldsa = run_mldsa_valid_and_negative(sig, iterations);
    write_result(csv, &mldsa);

    v31_result combined = run_combined_sequence(kem, sig, iterations);
    write_result(csv, &combined);

    fclose(csv);

    OQS_SIG_free(sig);
    OQS_KEM_free(kem);

    free(mlkem_ws);
    free(mldsa_ws);

    if (mlkem.failed == 0 && mldsa.failed == 0 && combined.failed == 0) {
        printf("\nv31 combined correctness: PASS\n");
        return 0;
    }

    printf("\nv31 combined correctness: FAIL\n");
    return 1;
}
