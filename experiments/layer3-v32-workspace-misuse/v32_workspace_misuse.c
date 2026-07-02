#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include "v32_workspace_setup.generated.h"

#ifndef OQS_KEM_alg_ml_kem_768
#define V32_MLKEM_ALG "ML-KEM-768"
#else
#define V32_MLKEM_ALG OQS_KEM_alg_ml_kem_768
#endif

#ifndef OQS_SIG_alg_ml_dsa_44
#define V32_MLDSA_ALG "ML-DSA-44"
#else
#define V32_MLDSA_ALG OQS_SIG_alg_ml_dsa_44
#endif

#define V32_ALIGN 64

typedef struct {
    FILE *csv;
    unsigned total;
    unsigned pass;
    unsigned fail;
    unsigned documented;
} v32_ctx;

static void v32_randombytes(uint8_t *out, size_t out_len) {
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

static int is_aligned(const void *p) {
    return (((uintptr_t) p) % V32_ALIGN) == 0;
}

static void *xcalloc(size_t n, size_t s) {
    void *p = calloc(n, s);
    if (p == NULL) {
        fprintf(stderr, "allocation failed: %zu x %zu\n", n, s);
        exit(2);
    }
    return p;
}

static void *xaligned_alloc(size_t bytes) {
    void *p = NULL;

    if (posix_memalign(&p, V32_ALIGN, bytes) != 0) {
        fprintf(stderr, "posix_memalign failed for %zu bytes\n", bytes);
        exit(2);
    }

    memset(p, 0, bytes);
    return p;
}

static void fill_message(uint8_t *msg, size_t len, uint64_t iter) {
    for (size_t i = 0; i < len; i++) {
        msg[i] = (uint8_t) ((i * 131u + iter * 17u + 0x42u) & 0xffu);
    }
}

static void record(
    v32_ctx *ctx,
    const char *test,
    const char *scheme,
    const char *kind,
    const char *expected,
    const char *observed,
    unsigned iterations,
    unsigned passed,
    unsigned failed,
    const char *status,
    const char *notes
) {
    fprintf(
        ctx->csv,
        "%s,%s,%s,%s,%s,%u,%u,%u,%s,%s\n",
        test,
        scheme,
        kind,
        expected,
        observed,
        iterations,
        passed,
        failed,
        status,
        notes
    );

    printf(
        "%-42s %-10s expected=%-22s observed=%-18s status=%s\n",
        test,
        scheme,
        expected,
        observed,
        status
    );

    ctx->total++;

    if (strcmp(status, "PASS") == 0) {
        ctx->pass++;
    } else if (strcmp(status, "DOCUMENTED") == 0) {
        ctx->documented++;
    } else {
        ctx->fail++;
    }
}

static int safe_mlkem_set(void *workspace, size_t cap) {
    size_t need = v32_mlkem_workspace_need();

    if (workspace == NULL) {
        return -1;
    }

    if (cap < need) {
        return -1;
    }

    if (!is_aligned(workspace)) {
        return -1;
    }

    return v32_mlkem_workspace_set(workspace, cap);
}

static int safe_mldsa_set(void *workspace, size_t cap) {
    size_t need = v32_mldsa_workspace_need();

    if (workspace == NULL) {
        return -1;
    }

    if (cap < need) {
        return -1;
    }

    if (!is_aligned(workspace)) {
        return -1;
    }

    return v32_mldsa_workspace_set(workspace, cap);
}

static int mlkem_flow(unsigned iterations) {
    OQS_KEM *kem = OQS_KEM_new(V32_MLKEM_ALG);
    if (kem == NULL) {
        return 0;
    }

    uint8_t *pk = xcalloc(kem->length_public_key, 1);
    uint8_t *sk = xcalloc(kem->length_secret_key, 1);
    uint8_t *ct = xcalloc(kem->length_ciphertext, 1);
    uint8_t *ss_enc = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ss_dec = xcalloc(kem->length_shared_secret, 1);

    int ok_all = 1;

    for (unsigned i = 0; i < iterations; i++) {
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

        if (!ok) {
            ok_all = 0;
            break;
        }
    }

    free(pk);
    free(sk);
    free(ct);
    free(ss_enc);
    free(ss_dec);
    OQS_KEM_free(kem);

    return ok_all;
}

static int mldsa_flow(unsigned iterations) {
    OQS_SIG *sig = OQS_SIG_new(V32_MLDSA_ALG);
    if (sig == NULL) {
        return 0;
    }

    const size_t msg_len = 96;

    uint8_t *pk = xcalloc(sig->length_public_key, 1);
    uint8_t *sk = xcalloc(sig->length_secret_key, 1);
    uint8_t *signature = xcalloc(sig->length_signature, 1);
    uint8_t *bad_signature = xcalloc(sig->length_signature, 1);
    uint8_t *msg = xcalloc(msg_len, 1);
    uint8_t *bad_msg = xcalloc(msg_len, 1);

    int ok_all = 1;

    for (unsigned i = 0; i < iterations; i++) {
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

        if (!ok) {
            ok_all = 0;
            break;
        }
    }

    free(pk);
    free(sk);
    free(signature);
    free(bad_signature);
    free(msg);
    free(bad_msg);
    OQS_SIG_free(sig);

    return ok_all;
}

static int combined_flow(unsigned iterations) {
    OQS_KEM *kem = OQS_KEM_new(V32_MLKEM_ALG);
    if (kem == NULL) {
        return 0;
    }

    OQS_SIG *sig = OQS_SIG_new(V32_MLDSA_ALG);
    if (sig == NULL) {
        OQS_KEM_free(kem);
        return 0;
    }

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

    int ok_all = 1;

    for (unsigned i = 0; i < iterations; i++) {
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

        if (!ok) {
            ok_all = 0;
            break;
        }
    }

    free(kem_pk);
    free(kem_sk);
    free(kem_ct);
    free(ss_enc);
    free(ss_dec);
    free(sig_pk);
    free(sig_sk);
    free(signature);
    free(transcript);

    OQS_SIG_free(sig);
    OQS_KEM_free(kem);

    return ok_all;
}

static void test_reject(v32_ctx *ctx, const char *name, const char *scheme, int rc, const char *notes) {
    if (rc != 0) {
        record(ctx, name, scheme, "safe_wrapper", "reject", "rejected", 1, 1, 0, "PASS", notes);
    } else {
        record(ctx, name, scheme, "safe_wrapper", "reject", "accepted", 1, 0, 1, "FAIL", notes);
    }
}

static void test_accept(v32_ctx *ctx, const char *name, const char *scheme, int rc, int flow_ok, unsigned iterations, const char *notes) {
    if (rc == 0 && flow_ok) {
        record(ctx, name, scheme, "safe_wrapper", "pass", "passed", iterations, iterations, 0, "PASS", notes);
    } else {
        record(ctx, name, scheme, "safe_wrapper", "pass", "failed", iterations, 0, iterations, "FAIL", notes);
    }
}

static int run_child_case(const char *case_name) {
    OQS_randombytes_custom_algorithm(v32_randombytes);

    size_t kem_need = v32_mlkem_workspace_need();
    size_t sig_need = v32_mldsa_workspace_need();

    if (strcmp(case_name, "mlkem_no_workspace") == 0) {
        return mlkem_flow(1) ? 0 : 1;
    }

    if (strcmp(case_name, "mldsa_no_workspace") == 0) {
        return mldsa_flow(1) ? 0 : 1;
    }

    if (strcmp(case_name, "combined_only_mlkem_set") == 0) {
        void *kem_ws = xaligned_alloc(kem_need);
        v32_mlkem_workspace_set(kem_ws, kem_need);
        int ok = combined_flow(1);
        free(kem_ws);
        return ok ? 0 : 1;
    }

    if (strcmp(case_name, "combined_only_mldsa_set") == 0) {
        void *sig_ws = xaligned_alloc(sig_need);
        v32_mldsa_workspace_set(sig_ws, sig_need);
        int ok = combined_flow(1);
        free(sig_ws);
        return ok ? 0 : 1;
    }

    if (strcmp(case_name, "mlkem_raw_null") == 0) {
        v32_mlkem_raw_set(NULL);
        return mlkem_flow(1) ? 0 : 1;
    }

    if (strcmp(case_name, "mldsa_raw_null") == 0) {
        v32_mldsa_raw_set(NULL);
        return mldsa_flow(1) ? 0 : 1;
    }

    if (strcmp(case_name, "mlkem_raw_too_small") == 0) {
        void *ws = xaligned_alloc(64);
        v32_mlkem_raw_set(ws);
        int ok = mlkem_flow(1);
        free(ws);
        return ok ? 0 : 1;
    }

    if (strcmp(case_name, "mldsa_raw_too_small") == 0) {
        void *ws = xaligned_alloc(64);
        v32_mldsa_raw_set(ws);
        int ok = mldsa_flow(1);
        free(ws);
        return ok ? 0 : 1;
    }

    if (strcmp(case_name, "mlkem_raw_misaligned") == 0) {
        uint8_t *base = xcalloc(kem_need + V32_ALIGN + 1, 1);
        void *bad = base + 1;
        v32_mlkem_raw_set(bad);
        int ok = mlkem_flow(1);
        free(base);
        return ok ? 0 : 1;
    }

    if (strcmp(case_name, "mldsa_raw_misaligned") == 0) {
        uint8_t *base = xcalloc(sig_need + V32_ALIGN + 1, 1);
        void *bad = base + 1;
        v32_mldsa_raw_set(bad);
        int ok = mldsa_flow(1);
        free(base);
        return ok ? 0 : 1;
    }

    return 3;
}

static void run_child_observation(v32_ctx *ctx, const char *self, const char *case_name, const char *scheme, const char *notes) {
    pid_t pid = fork();

    if (pid < 0) {
        record(ctx, case_name, scheme, "raw_child", "isolated_observation", "fork_failed", 1, 0, 1, "FAIL", notes);
        return;
    }

    if (pid == 0) {
        execl(self, self, "--child", case_name, (char *) NULL);
        _exit(127);
    }

    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        record(ctx, case_name, scheme, "raw_child", "isolated_observation", "wait_failed", 1, 0, 1, "FAIL", notes);
        return;
    }

    char observed[64];

    if (WIFEXITED(status)) {
        snprintf(observed, sizeof(observed), "exit_%d", WEXITSTATUS(status));
    } else if (WIFSIGNALED(status)) {
        snprintf(observed, sizeof(observed), "signal_%d", WTERMSIG(status));
    } else {
        snprintf(observed, sizeof(observed), "unknown");
    }

    record(ctx, case_name, scheme, "raw_child", "record_result", observed, 1, 1, 0, "DOCUMENTED", notes);
}

int main(int argc, char **argv) {
    if (argc >= 3 && strcmp(argv[1], "--child") == 0) {
        return run_child_case(argv[2]);
    }

    OQS_randombytes_custom_algorithm(v32_randombytes);

    const char *csv_path = "layer3-results/v32_workspace_misuse.csv";

    if (argc >= 2) {
        csv_path = argv[1];
    }

    unsigned iterations = 100;

    if (argc >= 3) {
        iterations = (unsigned) strtoul(argv[2], NULL, 10);
        if (iterations == 0) {
            iterations = 100;
        }
    }

    size_t kem_need = v32_mlkem_workspace_need();
    size_t sig_need = v32_mldsa_workspace_need();

    printf("v32 workspace misuse tests\n");
    printf("ML-KEM workspace bytes: %zu\n", kem_need);
    printf("ML-DSA workspace bytes: %zu\n", sig_need);
    printf("Combined workspace bytes: %zu\n\n", kem_need + sig_need);

    FILE *csv = fopen(csv_path, "w");
    if (csv == NULL) {
        perror("fopen csv");
        return 2;
    }

    v32_ctx ctx = {
        .csv = csv,
        .total = 0,
        .pass = 0,
        .fail = 0,
        .documented = 0,
    };

    fprintf(csv, "test,scheme,kind,expected,observed,iterations,passed,failed,status,notes\n");

    test_reject(&ctx, "mlkem_null_wrapper", "ML-KEM", safe_mlkem_set(NULL, kem_need), "NULL rejected before raw setter");
    test_reject(&ctx, "mldsa_null_wrapper", "ML-DSA", safe_mldsa_set(NULL, sig_need), "NULL rejected before raw setter");

    void *kem_exact = xaligned_alloc(kem_need);
    void *sig_exact = xaligned_alloc(sig_need);

    test_reject(&ctx, "mlkem_size_0_wrapper", "ML-KEM", safe_mlkem_set(kem_exact, 0), "capacity 0 rejected");
    test_reject(&ctx, "mlkem_size_1_wrapper", "ML-KEM", safe_mlkem_set(kem_exact, 1), "capacity 1 rejected");
    test_reject(&ctx, "mlkem_size_half_wrapper", "ML-KEM", safe_mlkem_set(kem_exact, kem_need / 2), "half capacity rejected");
    test_reject(&ctx, "mlkem_size_minus1_wrapper", "ML-KEM", safe_mlkem_set(kem_exact, kem_need - 1), "required minus one rejected");

    test_reject(&ctx, "mldsa_size_0_wrapper", "ML-DSA", safe_mldsa_set(sig_exact, 0), "capacity 0 rejected");
    test_reject(&ctx, "mldsa_size_1_wrapper", "ML-DSA", safe_mldsa_set(sig_exact, 1), "capacity 1 rejected");
    test_reject(&ctx, "mldsa_size_half_wrapper", "ML-DSA", safe_mldsa_set(sig_exact, sig_need / 2), "half capacity rejected");
    test_reject(&ctx, "mldsa_size_minus1_wrapper", "ML-DSA", safe_mldsa_set(sig_exact, sig_need - 1), "required minus one rejected");

    uint8_t *kem_base = xcalloc(kem_need + V32_ALIGN + 1, 1);
    uint8_t *sig_base = xcalloc(sig_need + V32_ALIGN + 1, 1);

    test_reject(&ctx, "mlkem_misaligned_wrapper", "ML-KEM", safe_mlkem_set(kem_base + 1, kem_need), "misaligned pointer rejected");
    test_reject(&ctx, "mldsa_misaligned_wrapper", "ML-DSA", safe_mldsa_set(sig_base + 1, sig_need), "misaligned pointer rejected");

    int kem_rc = safe_mlkem_set(kem_exact, kem_need);
    int kem_ok = 0;

    if (kem_rc == 0) {
        OQS_KEM *kem_obj = OQS_KEM_new(V32_MLKEM_ALG);
        if (kem_obj != NULL) {
            safe_mlkem_set(kem_exact, kem_need);
            OQS_KEM_free(kem_obj);
        }
        kem_ok = mlkem_flow(iterations);
    }

    test_accept(&ctx, "mlkem_exact_wrapper", "ML-KEM", kem_rc, kem_ok, iterations, "exact required capacity");

    int sig_rc = safe_mldsa_set(sig_exact, sig_need);
    int sig_ok = 0;

    if (sig_rc == 0) {
        OQS_SIG *sig_obj = OQS_SIG_new(V32_MLDSA_ALG);
        if (sig_obj != NULL) {
            safe_mldsa_set(sig_exact, sig_need);
            OQS_SIG_free(sig_obj);
        }
        sig_ok = mldsa_flow(iterations);
    }

    test_accept(&ctx, "mldsa_exact_wrapper", "ML-DSA", sig_rc, sig_ok, iterations, "exact required capacity");

    void *kem_large = xaligned_alloc(kem_need + 4096);
    void *sig_large = xaligned_alloc(sig_need + 4096);

    int kem_large_rc = safe_mlkem_set(kem_large, kem_need + 4096);
    int kem_large_ok = 0;

    if (kem_large_rc == 0) {
        kem_large_ok = mlkem_flow(iterations);
    }

    test_accept(&ctx, "mlkem_larger_wrapper", "ML-KEM", kem_large_rc, kem_large_ok, iterations, "required plus 4096 capacity");

    int sig_large_rc = safe_mldsa_set(sig_large, sig_need + 4096);
    int sig_large_ok = 0;

    if (sig_large_rc == 0) {
        sig_large_ok = mldsa_flow(iterations);
    }

    test_accept(&ctx, "mldsa_larger_wrapper", "ML-DSA", sig_large_rc, sig_large_ok, iterations, "required plus 4096 capacity");

    void *kem_a = xaligned_alloc(kem_need);
    void *kem_b = xaligned_alloc(kem_need);

    int kem_replace_rc = safe_mlkem_set(kem_a, kem_need);
    int kem_replace_ok_a = 0;
    int kem_replace_ok_b = 0;

    if (kem_replace_rc == 0) {
        kem_replace_ok_a = mlkem_flow(iterations);
        kem_replace_rc = safe_mlkem_set(kem_b, kem_need);
        if (kem_replace_rc == 0) {
            kem_replace_ok_b = mlkem_flow(iterations);
        }
    }

    test_accept(
        &ctx,
        "mlkem_replace_workspace",
        "ML-KEM",
        kem_replace_rc,
        kem_replace_ok_a && kem_replace_ok_b,
        iterations * 2,
        "set workspace A then workspace B"
    );

    void *sig_a = xaligned_alloc(sig_need);
    void *sig_b = xaligned_alloc(sig_need);

    int sig_replace_rc = safe_mldsa_set(sig_a, sig_need);
    int sig_replace_ok_a = 0;
    int sig_replace_ok_b = 0;

    if (sig_replace_rc == 0) {
        sig_replace_ok_a = mldsa_flow(iterations);
        sig_replace_rc = safe_mldsa_set(sig_b, sig_need);
        if (sig_replace_rc == 0) {
            sig_replace_ok_b = mldsa_flow(iterations);
        }
    }

    test_accept(
        &ctx,
        "mldsa_replace_workspace",
        "ML-DSA",
        sig_replace_rc,
        sig_replace_ok_a && sig_replace_ok_b,
        iterations * 2,
        "set workspace A then workspace B"
    );

    void *kem_combined = xaligned_alloc(kem_need);
    void *sig_combined = xaligned_alloc(sig_need);

    int combined_rc = safe_mlkem_set(kem_combined, kem_need);
    if (combined_rc == 0) {
        combined_rc = safe_mldsa_set(sig_combined, sig_need);
    }

    int combined_ok = 0;

    if (combined_rc == 0) {
        combined_ok = combined_flow(iterations);
    }

    test_accept(&ctx, "combined_valid_wrapper", "Combined", combined_rc, combined_ok, iterations, "both lifecycle workspaces valid");

    run_child_observation(&ctx, argv[0], "mlkem_no_workspace", "ML-KEM", "fresh child without ML-KEM workspace");
    run_child_observation(&ctx, argv[0], "mldsa_no_workspace", "ML-DSA", "fresh child without ML-DSA workspace");
    run_child_observation(&ctx, argv[0], "combined_only_mlkem_set", "Combined", "ML-KEM set; ML-DSA missing");
    run_child_observation(&ctx, argv[0], "combined_only_mldsa_set", "Combined", "ML-DSA set; ML-KEM missing");
    run_child_observation(&ctx, argv[0], "mlkem_raw_null", "ML-KEM", "raw setter with NULL");
    run_child_observation(&ctx, argv[0], "mldsa_raw_null", "ML-DSA", "raw setter with NULL");
    run_child_observation(&ctx, argv[0], "mlkem_raw_too_small", "ML-KEM", "raw setter with 64-byte allocation");
    run_child_observation(&ctx, argv[0], "mldsa_raw_too_small", "ML-DSA", "raw setter with 64-byte allocation");
    run_child_observation(&ctx, argv[0], "mlkem_raw_misaligned", "ML-KEM", "raw setter with pointer + 1");
    run_child_observation(&ctx, argv[0], "mldsa_raw_misaligned", "ML-DSA", "raw setter with pointer + 1");

    printf("\nSummary: total=%u pass=%u fail=%u documented=%u\n", ctx.total, ctx.pass, ctx.fail, ctx.documented);

    fclose(csv);

    free(kem_exact);
    free(sig_exact);
    free(kem_base);
    free(sig_base);
    free(kem_large);
    free(sig_large);
    free(kem_a);
    free(kem_b);
    free(sig_a);
    free(sig_b);
    free(kem_combined);
    free(sig_combined);

    return ctx.fail == 0 ? 0 : 1;
}
