#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "v38_workspace_setup.generated.h"

#ifdef OQS_KEM_alg_ml_kem_768
#define V38_MLKEM_ALG OQS_KEM_alg_ml_kem_768
#else
#define V38_MLKEM_ALG "ML-KEM-768"
#endif

#ifdef OQS_SIG_alg_ml_dsa_44
#define V38_MLDSA_ALG OQS_SIG_alg_ml_dsa_44
#else
#define V38_MLDSA_ALG "ML-DSA-44"
#endif

static volatile uint64_t v38_sink = 0;

static uint64_t v38_rng_state = 0x3838381234567890ULL;

static uint64_t v38_xorshift64star(void) {
    uint64_t x = v38_rng_state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    v38_rng_state = x;
    return x * 0x2545F4914F6CDD1DULL;
}

static void v38_randombytes(uint8_t *out, size_t outlen) {
    size_t i = 0;
    while (i < outlen) {
        uint64_t r = v38_xorshift64star();
        for (size_t j = 0; j < 8 && i < outlen; j++, i++) {
            out[i] = (uint8_t)(r >> (8 * j));
        }
    }
}

static uint64_t now_ns(void) {
    struct timespec ts;

#ifdef CLOCK_MONOTONIC_RAW
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
#else
    clock_gettime(CLOCK_MONOTONIC, &ts);
#endif

    return ((uint64_t)ts.tv_sec * 1000000000ULL) + (uint64_t)ts.tv_nsec;
}

static void consume_bytes(const uint8_t *buf, size_t len, int rc) {
    uint64_t x = (uint64_t)(uint32_t)rc;

    if (buf != NULL && len > 0) {
        size_t step = (len / 8) + 1;
        for (size_t i = 0; i < len; i += step) {
            x = (x * 1315423911ULL) ^ buf[i] ^ (uint64_t)i;
        }
    }

    v38_sink ^= x;
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

typedef struct {
    OQS_KEM *kem;
    OQS_SIG *sig;

    uint8_t *mlkem_workspace;
    uint8_t *mldsa_workspace;

    uint8_t *kem_pk;
    uint8_t *kem_sk;
    uint8_t *kem_ct_valid;
    uint8_t *kem_ct_invalid;
    uint8_t *kem_ss_valid;
    uint8_t *kem_ss_out;

    uint8_t *sig_pk;
    uint8_t *sig_sk;
    uint8_t *msg_fixed;
    uint8_t *msg_alt;
    size_t msg_len;
    uint8_t *sig_valid;
    uint8_t *sig_invalid;
    uint8_t *sig_work;
    size_t sig_valid_len;
    size_t sig_work_len;

    uint8_t *transcript_valid;
    uint8_t *transcript_modified;
    uint8_t *transcript_sig;
    size_t transcript_len;
    size_t transcript_sig_len;
} v38_ctx;

typedef struct {
    double sum;
    double sumsq;
    uint64_t n;
} v38_stats;

typedef struct {
    const char *name;
    int samples;
    int n0;
    int n1;
    double mean0;
    double mean1;
    double t_abs;
    double threshold;
    int exec_failures;
    const char *status;
    const char *notes;
} v38_result;

static void stats_add(v38_stats *s, double x) {
    s->sum += x;
    s->sumsq += x * x;
    s->n++;
}

static double stats_mean(const v38_stats *s) {
    if (s->n == 0) {
        return 0.0;
    }
    return s->sum / (double)s->n;
}

static double stats_var(const v38_stats *s) {
    if (s->n < 2) {
        return 0.0;
    }

    double n = (double)s->n;
    double mean = s->sum / n;
    double var = (s->sumsq - (n * mean * mean)) / (n - 1.0);

    if (var < 0.0) {
        var = 0.0;
    }

    return var;
}

static double welch_t_abs(const v38_stats *a, const v38_stats *b) {
    if (a->n < 2 || b->n < 2) {
        return INFINITY;
    }

    double mean_a = stats_mean(a);
    double mean_b = stats_mean(b);
    double var_a = stats_var(a);
    double var_b = stats_var(b);

    double denom = sqrt((var_a / (double)a->n) + (var_b / (double)b->n));

    if (denom == 0.0) {
        if (mean_a == mean_b) {
            return 0.0;
        }
        return INFINITY;
    }

    double t = (mean_a - mean_b) / denom;
    if (t < 0.0) {
        t = -t;
    }

    return t;
}

static void ctx_init(v38_ctx *ctx) {
    memset(ctx, 0, sizeof(*ctx));

    OQS_randombytes_custom_algorithm(v38_randombytes);

    const size_t mlkem_ws = v38_mlkem_workspace_need();
    const size_t mldsa_ws = v38_mldsa_workspace_need();

    ctx->mlkem_workspace = xaligned_malloc(64, mlkem_ws);
    ctx->mldsa_workspace = xaligned_malloc(64, mldsa_ws);

    memset(ctx->mlkem_workspace, 0xA5, mlkem_ws);
    memset(ctx->mldsa_workspace, 0x5A, mldsa_ws);

    if (v38_mlkem_workspace_set(ctx->mlkem_workspace) != 0) {
        fprintf(stderr, "V38_SETUP_FAIL,mlkem_workspace_set\n");
        exit(1);
    }

    if (v38_mldsa_workspace_set(ctx->mldsa_workspace) != 0) {
        fprintf(stderr, "V38_SETUP_FAIL,mldsa_workspace_set\n");
        exit(1);
    }

    ctx->kem = OQS_KEM_new(V38_MLKEM_ALG);
    ctx->sig = OQS_SIG_new(V38_MLDSA_ALG);

    if (ctx->kem == NULL || ctx->sig == NULL) {
        fprintf(stderr, "V38_SETUP_FAIL,OQS_new\n");
        exit(1);
    }

    ctx->kem_pk = xmalloc(ctx->kem->length_public_key);
    ctx->kem_sk = xmalloc(ctx->kem->length_secret_key);
    ctx->kem_ct_valid = xmalloc(ctx->kem->length_ciphertext);
    ctx->kem_ct_invalid = xmalloc(ctx->kem->length_ciphertext);
    ctx->kem_ss_valid = xmalloc(ctx->kem->length_shared_secret);
    ctx->kem_ss_out = xmalloc(ctx->kem->length_shared_secret);

    if (OQS_KEM_keypair(ctx->kem, ctx->kem_pk, ctx->kem_sk) != OQS_SUCCESS) {
        fprintf(stderr, "V38_SETUP_FAIL,OQS_KEM_keypair\n");
        exit(1);
    }

    if (OQS_KEM_encaps(ctx->kem, ctx->kem_ct_valid, ctx->kem_ss_valid, ctx->kem_pk) != OQS_SUCCESS) {
        fprintf(stderr, "V38_SETUP_FAIL,OQS_KEM_encaps\n");
        exit(1);
    }

    memcpy(ctx->kem_ct_invalid, ctx->kem_ct_valid, ctx->kem->length_ciphertext);
    ctx->kem_ct_invalid[0] ^= 0x01;

    ctx->sig_pk = xmalloc(ctx->sig->length_public_key);
    ctx->sig_sk = xmalloc(ctx->sig->length_secret_key);

    ctx->msg_len = 96;
    ctx->msg_fixed = xmalloc(ctx->msg_len);
    ctx->msg_alt = xmalloc(ctx->msg_len);

    fill_message(ctx->msg_fixed, ctx->msg_len, 0, 0x38);
    fill_message(ctx->msg_alt, ctx->msg_len, 1, 0x39);

    ctx->sig_valid = xmalloc(ctx->sig->length_signature);
    ctx->sig_invalid = xmalloc(ctx->sig->length_signature);
    ctx->sig_work = xmalloc(ctx->sig->length_signature);

    if (OQS_SIG_keypair(ctx->sig, ctx->sig_pk, ctx->sig_sk) != OQS_SUCCESS) {
        fprintf(stderr, "V38_SETUP_FAIL,OQS_SIG_keypair\n");
        exit(1);
    }

    if (OQS_SIG_sign(ctx->sig, ctx->sig_valid, &ctx->sig_valid_len, ctx->msg_fixed, ctx->msg_len, ctx->sig_sk) != OQS_SUCCESS) {
        fprintf(stderr, "V38_SETUP_FAIL,OQS_SIG_sign\n");
        exit(1);
    }

    memcpy(ctx->sig_invalid, ctx->sig_valid, ctx->sig_valid_len);
    if (ctx->sig_valid_len > 0) {
        ctx->sig_invalid[0] ^= 0x01;
    }

    ctx->transcript_len =
        ctx->kem->length_public_key +
        ctx->kem->length_ciphertext +
        ctx->kem->length_shared_secret;

    ctx->transcript_valid = xmalloc(ctx->transcript_len);
    ctx->transcript_modified = xmalloc(ctx->transcript_len);
    ctx->transcript_sig = xmalloc(ctx->sig->length_signature);

    size_t off = 0;
    memcpy(ctx->transcript_valid + off, ctx->kem_pk, ctx->kem->length_public_key);
    off += ctx->kem->length_public_key;
    memcpy(ctx->transcript_valid + off, ctx->kem_ct_valid, ctx->kem->length_ciphertext);
    off += ctx->kem->length_ciphertext;
    memcpy(ctx->transcript_valid + off, ctx->kem_ss_valid, ctx->kem->length_shared_secret);

    memcpy(ctx->transcript_modified, ctx->transcript_valid, ctx->transcript_len);
    ctx->transcript_modified[0] ^= 0x01;

    if (OQS_SIG_sign(
            ctx->sig,
            ctx->transcript_sig,
            &ctx->transcript_sig_len,
            ctx->transcript_valid,
            ctx->transcript_len,
            ctx->sig_sk
        ) != OQS_SUCCESS) {
        fprintf(stderr, "V38_SETUP_FAIL,OQS_SIG_sign_transcript\n");
        exit(1);
    }
}

static void ctx_free(v38_ctx *ctx) {
    if (ctx->kem != NULL) {
        OQS_KEM_free(ctx->kem);
    }
    if (ctx->sig != NULL) {
        OQS_SIG_free(ctx->sig);
    }

    free(ctx->mlkem_workspace);
    free(ctx->mldsa_workspace);

    free(ctx->kem_pk);
    free(ctx->kem_sk);
    free(ctx->kem_ct_valid);
    free(ctx->kem_ct_invalid);
    free(ctx->kem_ss_valid);
    free(ctx->kem_ss_out);

    free(ctx->sig_pk);
    free(ctx->sig_sk);
    free(ctx->msg_fixed);
    free(ctx->msg_alt);
    free(ctx->sig_valid);
    free(ctx->sig_invalid);
    free(ctx->sig_work);

    free(ctx->transcript_valid);
    free(ctx->transcript_modified);
    free(ctx->transcript_sig);

    memset(ctx, 0, sizeof(*ctx));
}

static int op_mlkem_decaps_valid_vs_invalid(v38_ctx *ctx, int class_id) {
    const uint8_t *ct = class_id == 0 ? ctx->kem_ct_valid : ctx->kem_ct_invalid;

    int rc = OQS_KEM_decaps(ctx->kem, ctx->kem_ss_out, ct, ctx->kem_sk);
    consume_bytes(ctx->kem_ss_out, ctx->kem->length_shared_secret, rc);

    /*
     * ML-KEM decapsulation generally returns OQS_SUCCESS even for invalid
     * ciphertexts after implicit rejection. Only valid-class failure is treated
     * as an execution failure here.
     */
    if (class_id == 0 && rc != OQS_SUCCESS) {
        return 1;
    }

    return 0;
}

static int op_mldsa_verify_valid_vs_invalid_sig(v38_ctx *ctx, int class_id) {
    const uint8_t *sigbuf = class_id == 0 ? ctx->sig_valid : ctx->sig_invalid;

    int rc = OQS_SIG_verify(
        ctx->sig,
        ctx->msg_fixed,
        ctx->msg_len,
        sigbuf,
        ctx->sig_valid_len,
        ctx->sig_pk
    );

    consume_bytes(sigbuf, ctx->sig_valid_len, rc);

    if (class_id == 0 && rc != OQS_SUCCESS) {
        return 1;
    }

    if (class_id == 1 && rc == OQS_SUCCESS) {
        return 1;
    }

    return 0;
}

static int op_mldsa_sign_fixed_vs_alt_msg(v38_ctx *ctx, int class_id) {
    const uint8_t *msg = class_id == 0 ? ctx->msg_fixed : ctx->msg_alt;
    ctx->sig_work_len = 0;

    int rc = OQS_SIG_sign(
        ctx->sig,
        ctx->sig_work,
        &ctx->sig_work_len,
        msg,
        ctx->msg_len,
        ctx->sig_sk
    );

    consume_bytes(ctx->sig_work, ctx->sig_work_len, rc);

    if (rc != OQS_SUCCESS) {
        return 1;
    }

    if (ctx->sig_work_len > ctx->sig->length_signature) {
        return 1;
    }

    return 0;
}

static int op_combined_verify_valid_vs_modified_transcript(v38_ctx *ctx, int class_id) {
    const uint8_t *msg = class_id == 0 ? ctx->transcript_valid : ctx->transcript_modified;

    int rc = OQS_SIG_verify(
        ctx->sig,
        msg,
        ctx->transcript_len,
        ctx->transcript_sig,
        ctx->transcript_sig_len,
        ctx->sig_pk
    );

    consume_bytes(msg, ctx->transcript_len, rc);

    if (class_id == 0 && rc != OQS_SUCCESS) {
        return 1;
    }

    if (class_id == 1 && rc == OQS_SUCCESS) {
        return 1;
    }

    return 0;
}

typedef int (*v38_op_fn)(v38_ctx *, int);

static v38_result run_timing_case(
    v38_ctx *ctx,
    const char *name,
    v38_op_fn fn,
    int samples,
    int warmup,
    int batch,
    double threshold,
    const char *notes
) {
    v38_stats s0 = {0};
    v38_stats s1 = {0};
    int exec_failures = 0;

    for (int i = 0; i < warmup; i++) {
        int cls = (int)(v38_xorshift64star() & 1ULL);
        exec_failures += fn(ctx, cls);
    }

    for (int i = 0; i < samples; i++) {
        int cls = (int)(v38_xorshift64star() & 1ULL);

        uint64_t t0 = now_ns();

        for (int j = 0; j < batch; j++) {
            exec_failures += fn(ctx, cls);
        }

        uint64_t t1 = now_ns();

        double delta = (double)(t1 - t0) / (double)batch;

        if (cls == 0) {
            stats_add(&s0, delta);
        } else {
            stats_add(&s1, delta);
        }
    }

    double t_abs = welch_t_abs(&s0, &s1);

    const char *status = "PASS";
    if (exec_failures != 0 || s0.n < 2 || s1.n < 2) {
        status = "FAIL";
    } else if (t_abs >= threshold) {
        status = "FLAG";
    }

    v38_result r;
    r.name = name;
    r.samples = samples;
    r.n0 = (int)s0.n;
    r.n1 = (int)s1.n;
    r.mean0 = stats_mean(&s0);
    r.mean1 = stats_mean(&s1);
    r.t_abs = t_abs;
    r.threshold = threshold;
    r.exec_failures = exec_failures;
    r.status = status;
    r.notes = notes;
    return r;
}

static void print_result(const v38_result *r) {
    printf(
        "V38_CASE,%s,%d,%d,%d,%.3f,%.3f,%.6f,%.3f,%d,%s,%s\n",
        r->name,
        r->samples,
        r->n0,
        r->n1,
        r->mean0,
        r->mean1,
        r->t_abs,
        r->threshold,
        r->exec_failures,
        r->status,
        r->notes
    );
}

int main(int argc, char **argv) {
    int samples = 2000;
    int warmup = 100;
    int batch = 1;
    double threshold = 4.5;

    if (argc >= 2) {
        samples = atoi(argv[1]);
    }
    if (argc >= 3) {
        warmup = atoi(argv[2]);
    }
    if (argc >= 4) {
        threshold = atof(argv[3]);
    }
    if (argc >= 5) {
        batch = atoi(argv[4]);
    }

    if (samples <= 10 || warmup < 0 || threshold <= 0.0 || batch <= 0) {
        fprintf(stderr, "usage: %s [samples>10] [warmup>=0] [threshold>0] [batch>0]\n", argv[0]);
        return 2;
    }

    v38_ctx ctx;
    ctx_init(&ctx);

    const size_t mlkem_ws = v38_mlkem_workspace_need();
    const size_t mldsa_ws = v38_mldsa_workspace_need();
    const size_t combined_ws = mlkem_ws + mldsa_ws;

    printf("V38_CONFIG,SAMPLES,%d\n", samples);
    printf("V38_CONFIG,WARMUP,%d\n", warmup);
    printf("V38_CONFIG,THRESHOLD,%.3f\n", threshold);
    printf("V38_CONFIG,BATCH,%d\n", batch);
    printf("V38_WORKSPACE,ML-KEM,%zu\n", mlkem_ws);
    printf("V38_WORKSPACE,ML-DSA,%zu\n", mldsa_ws);
    printf("V38_WORKSPACE,COMBINED,%zu\n", combined_ws);

    v38_result results[4];

    results[0] = run_timing_case(
        &ctx,
        "mlkem_decaps_valid_vs_invalid_ct",
        op_mlkem_decaps_valid_vs_invalid,
        samples,
        warmup,
        batch,
        threshold,
        "secret-key operation; valid ciphertext class vs modified ciphertext class"
    );

    results[1] = run_timing_case(
        &ctx,
        "mldsa_verify_valid_vs_invalid_sig",
        op_mldsa_verify_valid_vs_invalid_sig,
        samples,
        warmup,
        batch,
        threshold,
        "public verification operation; valid signature class vs modified signature class"
    );

    results[2] = run_timing_case(
        &ctx,
        "mldsa_sign_fixed_vs_alt_msg",
        op_mldsa_sign_fixed_vs_alt_msg,
        samples,
        warmup,
        batch,
        threshold,
        "secret-key operation; fixed message class vs alternate message class"
    );

    results[3] = run_timing_case(
        &ctx,
        "combined_verify_valid_vs_modified_transcript",
        op_combined_verify_valid_vs_modified_transcript,
        samples,
        warmup,
        batch,
        threshold,
        "combined transcript verification; valid transcript class vs modified transcript class"
    );

    int pass_rows = 0;
    int flag_rows = 0;
    int fail_rows = 0;

    for (int i = 0; i < 4; i++) {
        print_result(&results[i]);

        if (strcmp(results[i].status, "PASS") == 0) {
            pass_rows++;
        } else if (strcmp(results[i].status, "FLAG") == 0) {
            flag_rows++;
        } else {
            fail_rows++;
        }
    }

    printf(
        "V38_SUMMARY,%d,%d,%d,%d,%s\n",
        4,
        pass_rows,
        flag_rows,
        fail_rows,
        fail_rows == 0 ? "PASS" : "FAIL"
    );

    consume_bytes((const uint8_t *)&v38_sink, sizeof(v38_sink), 0);

    ctx_free(&ctx);

    return fail_rows == 0 ? 0 : 1;
}
