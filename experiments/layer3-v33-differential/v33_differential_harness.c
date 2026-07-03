#define _POSIX_C_SOURCE 200809L

#include <oqs/oqs.h>

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef V33_OPTIMIZED
#define V33_OPTIMIZED 0
#endif

#if V33_OPTIMIZED
#include "v33_workspace_setup.generated.h"
#endif

#ifndef OQS_KEM_alg_ml_kem_768
#define V33_MLKEM_ALG "ML-KEM-768"
#else
#define V33_MLKEM_ALG OQS_KEM_alg_ml_kem_768
#endif

#ifndef OQS_SIG_alg_ml_dsa_44
#define V33_MLDSA_ALG "ML-DSA-44"
#else
#define V33_MLDSA_ALG OQS_SIG_alg_ml_dsa_44
#endif

#define V33_KEM_MAGIC      0x334B454Du
#define V33_SIG_MAGIC      0x33534947u
#define V33_COMBINED_MAGIC 0x33434F4Du

#define V33_MSG_LEN 96u
#define V33_ALIGN 64u

static uint64_t v33_rng_state = 0x9e3779b97f4a7c15ULL;

#if V33_OPTIMIZED
static void *g_mlkem_ws = NULL;
static void *g_mldsa_ws = NULL;
static size_t g_mlkem_ws_bytes = 0;
static size_t g_mldsa_ws_bytes = 0;
#endif

static uint64_t fnv1a64(const char *s) {
    uint64_t h = 1469598103934665603ULL;

    while (*s) {
        h ^= (unsigned char) *s;
        h *= 1099511628211ULL;
        s++;
    }

    return h;
}

static void v33_seed_rng(const char *mode) {
    const char *seed_env = getenv("V33_RNG_SEED");
    uint64_t seed = 0x76543210abcdef55ULL;

    if (seed_env != NULL && seed_env[0] != '\0') {
        seed ^= fnv1a64(seed_env);
    }

    seed ^= fnv1a64(mode);

    if (seed == 0) {
        seed = 0x9e3779b97f4a7c15ULL;
    }

    v33_rng_state = seed;
}

static uint64_t xorshift64star(void) {
    uint64_t x = v33_rng_state;

    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;

    v33_rng_state = x;

    return x * 2685821657736338717ULL;
}

static void v33_randombytes(uint8_t *out, size_t out_len) {
    size_t off = 0;

    while (off < out_len) {
        uint64_t r = xorshift64star();

        for (size_t j = 0; j < 8 && off < out_len; j++) {
            out[off++] = (uint8_t) ((r >> (8 * j)) & 0xffu);
        }
    }
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

    if (posix_memalign(&p, V33_ALIGN, bytes) != 0) {
        fprintf(stderr, "posix_memalign failed for %zu bytes\n", bytes);
        exit(2);
    }

    memset(p, 0, bytes);
    return p;
}

static int write_exact(FILE *f, const void *buf, size_t len) {
    return fwrite(buf, 1, len, f) == len;
}

static int read_exact(FILE *f, void *buf, size_t len) {
    return fread(buf, 1, len, f) == len;
}

static int write_u32(FILE *f, uint32_t v) {
    return write_exact(f, &v, sizeof(v));
}

static int read_u32(FILE *f, uint32_t *v) {
    return read_exact(f, v, sizeof(*v));
}

static int write_u64(FILE *f, uint64_t v) {
    return write_exact(f, &v, sizeof(v));
}

static int read_u64(FILE *f, uint64_t *v) {
    return read_exact(f, v, sizeof(*v));
}

static void fill_message(uint8_t *msg, size_t len, uint64_t iter) {
    for (size_t i = 0; i < len; i++) {
        msg[i] = (uint8_t) ((i * 131u + iter * 17u + 0x42u) & 0xffu);
    }
}

static void result_line(const char *mode, uint32_t iterations, uint32_t passed, uint32_t failed) {
    printf(
        "V33_RESULT,%s,%u,%u,%u,%s\n",
        mode,
        iterations,
        passed,
        failed,
        failed == 0 ? "PASS" : "FAIL"
    );
}

#if V33_OPTIMIZED
static void v33_workspace_init(void) {
    g_mlkem_ws_bytes = v33_mlkem_workspace_need();
    g_mldsa_ws_bytes = v33_mldsa_workspace_need();

    g_mlkem_ws = xaligned_alloc(g_mlkem_ws_bytes);
    g_mldsa_ws = xaligned_alloc(g_mldsa_ws_bytes);

    if (v33_mlkem_workspace_set(g_mlkem_ws, g_mlkem_ws_bytes) != 0) {
        fprintf(stderr, "failed to set ML-KEM workspace\n");
        exit(2);
    }

    if (v33_mldsa_workspace_set(g_mldsa_ws, g_mldsa_ws_bytes) != 0) {
        fprintf(stderr, "failed to set ML-DSA workspace\n");
        exit(2);
    }

    fprintf(stderr, "optimized workspace: ML-KEM=%zu ML-DSA=%zu combined=%zu\n",
            g_mlkem_ws_bytes,
            g_mldsa_ws_bytes,
            g_mlkem_ws_bytes + g_mldsa_ws_bytes);
}

static void v33_workspace_free(void) {
    free(g_mlkem_ws);
    free(g_mldsa_ws);
    g_mlkem_ws = NULL;
    g_mldsa_ws = NULL;
}

static void v33_refresh_mlkem_workspace(void) {
    if (v33_mlkem_workspace_set(g_mlkem_ws, g_mlkem_ws_bytes) != 0) {
        fprintf(stderr, "failed to refresh ML-KEM workspace\n");
        exit(2);
    }
}

static void v33_refresh_mldsa_workspace(void) {
    if (v33_mldsa_workspace_set(g_mldsa_ws, g_mldsa_ws_bytes) != 0) {
        fprintf(stderr, "failed to refresh ML-DSA workspace\n");
        exit(2);
    }
}
#else
static void v33_workspace_init(void) {}
static void v33_workspace_free(void) {}
static void v33_refresh_mlkem_workspace(void) {}
static void v33_refresh_mldsa_workspace(void) {}
#endif

static void make_transcript(
    uint8_t *out,
    const uint8_t *kem_pk,
    size_t kem_pk_len,
    const uint8_t *kem_ct,
    size_t kem_ct_len,
    const uint8_t *ss,
    size_t ss_len
) {
    size_t off = 0;

    memcpy(out + off, kem_pk, kem_pk_len);
    off += kem_pk_len;

    memcpy(out + off, kem_ct, kem_ct_len);
    off += kem_ct_len;

    memcpy(out + off, ss, ss_len);
}

static int mlkem_gen(const char *path, uint32_t iterations) {
    OQS_KEM *kem = OQS_KEM_new(V33_MLKEM_ALG);

    if (kem == NULL) {
        fprintf(stderr, "OQS_KEM_new failed for %s\n", V33_MLKEM_ALG);
        result_line("mlkem_gen", iterations, 0, iterations);
        return 1;
    }

    v33_refresh_mlkem_workspace();

    FILE *f = fopen(path, "wb");

    if (f == NULL) {
        perror("fopen mlkem_gen");
        OQS_KEM_free(kem);
        result_line("mlkem_gen", iterations, 0, iterations);
        return 1;
    }

    uint8_t *pk = xcalloc(kem->length_public_key, 1);
    uint8_t *sk = xcalloc(kem->length_secret_key, 1);
    uint8_t *ct = xcalloc(kem->length_ciphertext, 1);
    uint8_t *ss_enc = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ss_dec = xcalloc(kem->length_shared_secret, 1);

    uint32_t passed = 0;
    uint32_t failed = 0;

    int header_ok =
        write_u32(f, V33_KEM_MAGIC) &&
        write_u32(f, iterations) &&
        write_u64(f, (uint64_t) kem->length_public_key) &&
        write_u64(f, (uint64_t) kem->length_secret_key) &&
        write_u64(f, (uint64_t) kem->length_ciphertext) &&
        write_u64(f, (uint64_t) kem->length_shared_secret);

    if (!header_ok) {
        failed = iterations;
        goto done;
    }

    for (uint32_t i = 0; i < iterations; i++) {
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
            ok =
                write_exact(f, pk, kem->length_public_key) &&
                write_exact(f, sk, kem->length_secret_key) &&
                write_exact(f, ct, kem->length_ciphertext) &&
                write_exact(f, ss_enc, kem->length_shared_secret);
        }

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

done:
    fclose(f);

    free(pk);
    free(sk);
    free(ct);
    free(ss_enc);
    free(ss_dec);

    OQS_KEM_free(kem);

    result_line("mlkem_gen", iterations, passed, failed);
    return failed == 0 ? 0 : 1;
}

static int mlkem_consume(const char *path, uint32_t unused_iterations) {
    (void) unused_iterations;

    OQS_KEM *kem = OQS_KEM_new(V33_MLKEM_ALG);

    if (kem == NULL) {
        fprintf(stderr, "OQS_KEM_new failed for %s\n", V33_MLKEM_ALG);
        result_line("mlkem_consume", 0, 0, 1);
        return 1;
    }

    v33_refresh_mlkem_workspace();

    FILE *f = fopen(path, "rb");

    if (f == NULL) {
        perror("fopen mlkem_consume");
        OQS_KEM_free(kem);
        result_line("mlkem_consume", 0, 0, 1);
        return 1;
    }

    uint32_t magic = 0;
    uint32_t iterations = 0;
    uint64_t pk_len = 0;
    uint64_t sk_len = 0;
    uint64_t ct_len = 0;
    uint64_t ss_len = 0;

    int header_ok =
        read_u32(f, &magic) &&
        read_u32(f, &iterations) &&
        read_u64(f, &pk_len) &&
        read_u64(f, &sk_len) &&
        read_u64(f, &ct_len) &&
        read_u64(f, &ss_len);

    if (!header_ok || magic != V33_KEM_MAGIC ||
        pk_len != kem->length_public_key ||
        sk_len != kem->length_secret_key ||
        ct_len != kem->length_ciphertext ||
        ss_len != kem->length_shared_secret) {
        fclose(f);
        OQS_KEM_free(kem);
        result_line("mlkem_consume", iterations, 0, iterations ? iterations : 1);
        return 1;
    }

    uint8_t *pk = xcalloc(kem->length_public_key, 1);
    uint8_t *sk = xcalloc(kem->length_secret_key, 1);
    uint8_t *ct = xcalloc(kem->length_ciphertext, 1);
    uint8_t *ss_expected = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ss_dec = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ct_local = xcalloc(kem->length_ciphertext, 1);
    uint8_t *ss_local_enc = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ss_local_dec = xcalloc(kem->length_shared_secret, 1);

    uint32_t passed = 0;
    uint32_t failed = 0;

    for (uint32_t i = 0; i < iterations; i++) {
        int ok =
            read_exact(f, pk, kem->length_public_key) &&
            read_exact(f, sk, kem->length_secret_key) &&
            read_exact(f, ct, kem->length_ciphertext) &&
            read_exact(f, ss_expected, kem->length_shared_secret);

        if (ok && OQS_KEM_decaps(kem, ss_dec, ct, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && memcmp(ss_dec, ss_expected, kem->length_shared_secret) != 0) {
            ok = 0;
        }

        if (ok && OQS_KEM_encaps(kem, ct_local, ss_local_enc, pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_KEM_decaps(kem, ss_local_dec, ct_local, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && memcmp(ss_local_enc, ss_local_dec, kem->length_shared_secret) != 0) {
            ok = 0;
        }

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

    fclose(f);

    free(pk);
    free(sk);
    free(ct);
    free(ss_expected);
    free(ss_dec);
    free(ct_local);
    free(ss_local_enc);
    free(ss_local_dec);

    OQS_KEM_free(kem);

    result_line("mlkem_consume", iterations, passed, failed);
    return failed == 0 ? 0 : 1;
}

static int mldsa_gen(const char *path, uint32_t iterations) {
    OQS_SIG *sig = OQS_SIG_new(V33_MLDSA_ALG);

    if (sig == NULL) {
        fprintf(stderr, "OQS_SIG_new failed for %s\n", V33_MLDSA_ALG);
        result_line("mldsa_gen", iterations, 0, iterations);
        return 1;
    }

    v33_refresh_mldsa_workspace();

    FILE *f = fopen(path, "wb");

    if (f == NULL) {
        perror("fopen mldsa_gen");
        OQS_SIG_free(sig);
        result_line("mldsa_gen", iterations, 0, iterations);
        return 1;
    }

    uint8_t *pk = xcalloc(sig->length_public_key, 1);
    uint8_t *sk = xcalloc(sig->length_secret_key, 1);
    uint8_t *msg = xcalloc(V33_MSG_LEN, 1);
    uint8_t *signature = xcalloc(sig->length_signature, 1);
    uint8_t *bad_msg = xcalloc(V33_MSG_LEN, 1);
    uint8_t *bad_sig = xcalloc(sig->length_signature, 1);

    uint32_t passed = 0;
    uint32_t failed = 0;

    int header_ok =
        write_u32(f, V33_SIG_MAGIC) &&
        write_u32(f, iterations) &&
        write_u64(f, (uint64_t) sig->length_public_key) &&
        write_u64(f, (uint64_t) sig->length_secret_key) &&
        write_u64(f, (uint64_t) sig->length_signature) &&
        write_u64(f, (uint64_t) V33_MSG_LEN);

    if (!header_ok) {
        failed = iterations;
        goto done;
    }

    for (uint32_t i = 0; i < iterations; i++) {
        int ok = 1;
        size_t sig_len = 0;

        fill_message(msg, V33_MSG_LEN, i);

        if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        memset(signature, 0, sig->length_signature);

        if (ok && OQS_SIG_sign(sig, signature, &sig_len, msg, V33_MSG_LEN, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_SIG_verify(sig, msg, V33_MSG_LEN, signature, sig_len, pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok) {
            memcpy(bad_msg, msg, V33_MSG_LEN);
            bad_msg[0] ^= 0x01;

            if (OQS_SIG_verify(sig, bad_msg, V33_MSG_LEN, signature, sig_len, pk) == OQS_SUCCESS) {
                ok = 0;
            }
        }

        if (ok) {
            memcpy(bad_sig, signature, sig->length_signature);
            if (sig_len > 0) {
                bad_sig[0] ^= 0x01;
            }

            if (OQS_SIG_verify(sig, msg, V33_MSG_LEN, bad_sig, sig_len, pk) == OQS_SUCCESS) {
                ok = 0;
            }
        }

        if (ok) {
            ok =
                write_exact(f, pk, sig->length_public_key) &&
                write_exact(f, sk, sig->length_secret_key) &&
                write_exact(f, msg, V33_MSG_LEN) &&
                write_u64(f, (uint64_t) sig_len) &&
                write_exact(f, signature, sig->length_signature);
        }

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

done:
    fclose(f);

    free(pk);
    free(sk);
    free(msg);
    free(signature);
    free(bad_msg);
    free(bad_sig);

    OQS_SIG_free(sig);

    result_line("mldsa_gen", iterations, passed, failed);
    return failed == 0 ? 0 : 1;
}

static int mldsa_consume(const char *path, uint32_t unused_iterations) {
    (void) unused_iterations;

    OQS_SIG *sig = OQS_SIG_new(V33_MLDSA_ALG);

    if (sig == NULL) {
        fprintf(stderr, "OQS_SIG_new failed for %s\n", V33_MLDSA_ALG);
        result_line("mldsa_consume", 0, 0, 1);
        return 1;
    }

    v33_refresh_mldsa_workspace();

    FILE *f = fopen(path, "rb");

    if (f == NULL) {
        perror("fopen mldsa_consume");
        OQS_SIG_free(sig);
        result_line("mldsa_consume", 0, 0, 1);
        return 1;
    }

    uint32_t magic = 0;
    uint32_t iterations = 0;
    uint64_t pk_len = 0;
    uint64_t sk_len = 0;
    uint64_t sig_max = 0;
    uint64_t msg_len = 0;

    int header_ok =
        read_u32(f, &magic) &&
        read_u32(f, &iterations) &&
        read_u64(f, &pk_len) &&
        read_u64(f, &sk_len) &&
        read_u64(f, &sig_max) &&
        read_u64(f, &msg_len);

    if (!header_ok || magic != V33_SIG_MAGIC ||
        pk_len != sig->length_public_key ||
        sk_len != sig->length_secret_key ||
        sig_max != sig->length_signature ||
        msg_len != V33_MSG_LEN) {
        fclose(f);
        OQS_SIG_free(sig);
        result_line("mldsa_consume", iterations, 0, iterations ? iterations : 1);
        return 1;
    }

    uint8_t *pk = xcalloc(sig->length_public_key, 1);
    uint8_t *sk = xcalloc(sig->length_secret_key, 1);
    uint8_t *msg = xcalloc(V33_MSG_LEN, 1);
    uint8_t *signature = xcalloc(sig->length_signature, 1);
    uint8_t *bad_msg = xcalloc(V33_MSG_LEN, 1);
    uint8_t *bad_sig = xcalloc(sig->length_signature, 1);
    uint8_t *local_sig = xcalloc(sig->length_signature, 1);

    uint32_t passed = 0;
    uint32_t failed = 0;

    for (uint32_t i = 0; i < iterations; i++) {
        int ok = 1;
        uint64_t sig_len_u64 = 0;
        size_t local_sig_len = 0;

        ok =
            read_exact(f, pk, sig->length_public_key) &&
            read_exact(f, sk, sig->length_secret_key) &&
            read_exact(f, msg, V33_MSG_LEN) &&
            read_u64(f, &sig_len_u64) &&
            read_exact(f, signature, sig->length_signature);

        if (sig_len_u64 > sig->length_signature) {
            ok = 0;
        }

        if (ok && OQS_SIG_verify(sig, msg, V33_MSG_LEN, signature, (size_t) sig_len_u64, pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok) {
            memcpy(bad_msg, msg, V33_MSG_LEN);
            bad_msg[0] ^= 0x01;

            if (OQS_SIG_verify(sig, bad_msg, V33_MSG_LEN, signature, (size_t) sig_len_u64, pk) == OQS_SUCCESS) {
                ok = 0;
            }
        }

        if (ok) {
            memcpy(bad_sig, signature, sig->length_signature);
            if (sig_len_u64 > 0) {
                bad_sig[0] ^= 0x01;
            }

            if (OQS_SIG_verify(sig, msg, V33_MSG_LEN, bad_sig, (size_t) sig_len_u64, pk) == OQS_SUCCESS) {
                ok = 0;
            }
        }

        memset(local_sig, 0, sig->length_signature);

        if (ok && OQS_SIG_sign(sig, local_sig, &local_sig_len, msg, V33_MSG_LEN, sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_SIG_verify(sig, msg, V33_MSG_LEN, local_sig, local_sig_len, pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

    fclose(f);

    free(pk);
    free(sk);
    free(msg);
    free(signature);
    free(bad_msg);
    free(bad_sig);
    free(local_sig);

    OQS_SIG_free(sig);

    result_line("mldsa_consume", iterations, passed, failed);
    return failed == 0 ? 0 : 1;
}

static int combined_gen(const char *path, uint32_t iterations) {
    OQS_KEM *kem = OQS_KEM_new(V33_MLKEM_ALG);

    if (kem == NULL) {
        fprintf(stderr, "OQS_KEM_new failed for %s\n", V33_MLKEM_ALG);
        result_line("combined_gen", iterations, 0, iterations);
        return 1;
    }

    v33_refresh_mlkem_workspace();

    OQS_SIG *sig = OQS_SIG_new(V33_MLDSA_ALG);

    if (sig == NULL) {
        fprintf(stderr, "OQS_SIG_new failed for %s\n", V33_MLDSA_ALG);
        OQS_KEM_free(kem);
        result_line("combined_gen", iterations, 0, iterations);
        return 1;
    }

    v33_refresh_mldsa_workspace();

    FILE *f = fopen(path, "wb");

    if (f == NULL) {
        perror("fopen combined_gen");
        OQS_SIG_free(sig);
        OQS_KEM_free(kem);
        result_line("combined_gen", iterations, 0, iterations);
        return 1;
    }

    const size_t transcript_len =
        kem->length_public_key +
        kem->length_ciphertext +
        kem->length_shared_secret;

    uint8_t *kem_pk = xcalloc(kem->length_public_key, 1);
    uint8_t *kem_sk = xcalloc(kem->length_secret_key, 1);
    uint8_t *kem_ct = xcalloc(kem->length_ciphertext, 1);
    uint8_t *ss_enc = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ss_dec = xcalloc(kem->length_shared_secret, 1);

    uint8_t *sig_pk = xcalloc(sig->length_public_key, 1);
    uint8_t *sig_sk = xcalloc(sig->length_secret_key, 1);
    uint8_t *signature = xcalloc(sig->length_signature, 1);
    uint8_t *transcript = xcalloc(transcript_len, 1);

    uint32_t passed = 0;
    uint32_t failed = 0;

    int header_ok =
        write_u32(f, V33_COMBINED_MAGIC) &&
        write_u32(f, iterations) &&
        write_u64(f, (uint64_t) kem->length_public_key) &&
        write_u64(f, (uint64_t) kem->length_secret_key) &&
        write_u64(f, (uint64_t) kem->length_ciphertext) &&
        write_u64(f, (uint64_t) kem->length_shared_secret) &&
        write_u64(f, (uint64_t) sig->length_public_key) &&
        write_u64(f, (uint64_t) sig->length_signature) &&
        write_u64(f, (uint64_t) transcript_len);

    if (!header_ok) {
        failed = iterations;
        goto done;
    }

    for (uint32_t i = 0; i < iterations; i++) {
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
            make_transcript(
                transcript,
                kem_pk,
                kem->length_public_key,
                kem_ct,
                kem->length_ciphertext,
                ss_enc,
                kem->length_shared_secret
            );
        }

        memset(signature, 0, sig->length_signature);

        if (ok && OQS_SIG_sign(sig, signature, &sig_len, transcript, transcript_len, sig_sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && OQS_SIG_verify(sig, transcript, transcript_len, signature, sig_len, sig_pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok) {
            ok =
                write_exact(f, kem_pk, kem->length_public_key) &&
                write_exact(f, kem_sk, kem->length_secret_key) &&
                write_exact(f, kem_ct, kem->length_ciphertext) &&
                write_exact(f, ss_enc, kem->length_shared_secret) &&
                write_exact(f, sig_pk, sig->length_public_key) &&
                write_u64(f, (uint64_t) sig_len) &&
                write_exact(f, signature, sig->length_signature);
        }

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

done:
    fclose(f);

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

    result_line("combined_gen", iterations, passed, failed);
    return failed == 0 ? 0 : 1;
}

static int combined_consume(const char *path, uint32_t unused_iterations) {
    (void) unused_iterations;

    OQS_KEM *kem = OQS_KEM_new(V33_MLKEM_ALG);

    if (kem == NULL) {
        fprintf(stderr, "OQS_KEM_new failed for %s\n", V33_MLKEM_ALG);
        result_line("combined_consume", 0, 0, 1);
        return 1;
    }

    v33_refresh_mlkem_workspace();

    OQS_SIG *sig = OQS_SIG_new(V33_MLDSA_ALG);

    if (sig == NULL) {
        fprintf(stderr, "OQS_SIG_new failed for %s\n", V33_MLDSA_ALG);
        OQS_KEM_free(kem);
        result_line("combined_consume", 0, 0, 1);
        return 1;
    }

    v33_refresh_mldsa_workspace();

    FILE *f = fopen(path, "rb");

    if (f == NULL) {
        perror("fopen combined_consume");
        OQS_SIG_free(sig);
        OQS_KEM_free(kem);
        result_line("combined_consume", 0, 0, 1);
        return 1;
    }

    uint32_t magic = 0;
    uint32_t iterations = 0;
    uint64_t kem_pk_len = 0;
    uint64_t kem_sk_len = 0;
    uint64_t kem_ct_len = 0;
    uint64_t kem_ss_len = 0;
    uint64_t sig_pk_len = 0;
    uint64_t sig_max = 0;
    uint64_t transcript_len_u64 = 0;

    int header_ok =
        read_u32(f, &magic) &&
        read_u32(f, &iterations) &&
        read_u64(f, &kem_pk_len) &&
        read_u64(f, &kem_sk_len) &&
        read_u64(f, &kem_ct_len) &&
        read_u64(f, &kem_ss_len) &&
        read_u64(f, &sig_pk_len) &&
        read_u64(f, &sig_max) &&
        read_u64(f, &transcript_len_u64);

    const size_t transcript_len =
        kem->length_public_key +
        kem->length_ciphertext +
        kem->length_shared_secret;

    if (!header_ok || magic != V33_COMBINED_MAGIC ||
        kem_pk_len != kem->length_public_key ||
        kem_sk_len != kem->length_secret_key ||
        kem_ct_len != kem->length_ciphertext ||
        kem_ss_len != kem->length_shared_secret ||
        sig_pk_len != sig->length_public_key ||
        sig_max != sig->length_signature ||
        transcript_len_u64 != transcript_len) {
        fclose(f);
        OQS_SIG_free(sig);
        OQS_KEM_free(kem);
        result_line("combined_consume", iterations, 0, iterations ? iterations : 1);
        return 1;
    }

    uint8_t *kem_pk = xcalloc(kem->length_public_key, 1);
    uint8_t *kem_sk = xcalloc(kem->length_secret_key, 1);
    uint8_t *kem_ct = xcalloc(kem->length_ciphertext, 1);
    uint8_t *ss_expected = xcalloc(kem->length_shared_secret, 1);
    uint8_t *ss_dec = xcalloc(kem->length_shared_secret, 1);

    uint8_t *sig_pk = xcalloc(sig->length_public_key, 1);
    uint8_t *signature = xcalloc(sig->length_signature, 1);
    uint8_t *bad_signature = xcalloc(sig->length_signature, 1);

    uint8_t *transcript = xcalloc(transcript_len, 1);
    uint8_t *bad_transcript = xcalloc(transcript_len, 1);

    uint32_t passed = 0;
    uint32_t failed = 0;

    for (uint32_t i = 0; i < iterations; i++) {
        int ok = 1;
        uint64_t sig_len_u64 = 0;

        ok =
            read_exact(f, kem_pk, kem->length_public_key) &&
            read_exact(f, kem_sk, kem->length_secret_key) &&
            read_exact(f, kem_ct, kem->length_ciphertext) &&
            read_exact(f, ss_expected, kem->length_shared_secret) &&
            read_exact(f, sig_pk, sig->length_public_key) &&
            read_u64(f, &sig_len_u64) &&
            read_exact(f, signature, sig->length_signature);

        if (sig_len_u64 > sig->length_signature) {
            ok = 0;
        }

        if (ok && OQS_KEM_decaps(kem, ss_dec, kem_ct, kem_sk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok && memcmp(ss_dec, ss_expected, kem->length_shared_secret) != 0) {
            ok = 0;
        }

        if (ok) {
            make_transcript(
                transcript,
                kem_pk,
                kem->length_public_key,
                kem_ct,
                kem->length_ciphertext,
                ss_dec,
                kem->length_shared_secret
            );
        }

        if (ok && OQS_SIG_verify(sig, transcript, transcript_len, signature, (size_t) sig_len_u64, sig_pk) != OQS_SUCCESS) {
            ok = 0;
        }

        if (ok) {
            memcpy(bad_transcript, transcript, transcript_len);
            bad_transcript[0] ^= 0x01;

            if (OQS_SIG_verify(sig, bad_transcript, transcript_len, signature, (size_t) sig_len_u64, sig_pk) == OQS_SUCCESS) {
                ok = 0;
            }
        }

        if (ok) {
            memcpy(bad_signature, signature, sig->length_signature);
            if (sig_len_u64 > 0) {
                bad_signature[0] ^= 0x01;
            }

            if (OQS_SIG_verify(sig, transcript, transcript_len, bad_signature, (size_t) sig_len_u64, sig_pk) == OQS_SUCCESS) {
                ok = 0;
            }
        }

        if (ok) {
            passed++;
        } else {
            failed++;
        }
    }

    fclose(f);

    free(kem_pk);
    free(kem_sk);
    free(kem_ct);
    free(ss_expected);
    free(ss_dec);
    free(sig_pk);
    free(signature);
    free(bad_signature);
    free(transcript);
    free(bad_transcript);

    OQS_SIG_free(sig);
    OQS_KEM_free(kem);

    result_line("combined_consume", iterations, passed, failed);
    return failed == 0 ? 0 : 1;
}

static void usage(const char *argv0) {
    fprintf(stderr, "usage: %s <mode> <vector-file> <iterations>\n", argv0);
    fprintf(stderr, "modes:\n");
    fprintf(stderr, "  mlkem_gen\n");
    fprintf(stderr, "  mlkem_consume\n");
    fprintf(stderr, "  mldsa_gen\n");
    fprintf(stderr, "  mldsa_consume\n");
    fprintf(stderr, "  combined_gen\n");
    fprintf(stderr, "  combined_consume\n");
}

int main(int argc, char **argv) {
    if (argc != 4) {
        usage(argv[0]);
        return 2;
    }

    const char *mode = argv[1];
    const char *path = argv[2];
    uint32_t iterations = (uint32_t) strtoul(argv[3], NULL, 10);

    if (iterations == 0) {
        iterations = 100;
    }

    v33_seed_rng(mode);
    OQS_randombytes_custom_algorithm(v33_randombytes);

    v33_workspace_init();

    int rc = 2;

    if (strcmp(mode, "mlkem_gen") == 0) {
        rc = mlkem_gen(path, iterations);
    } else if (strcmp(mode, "mlkem_consume") == 0) {
        rc = mlkem_consume(path, iterations);
    } else if (strcmp(mode, "mldsa_gen") == 0) {
        rc = mldsa_gen(path, iterations);
    } else if (strcmp(mode, "mldsa_consume") == 0) {
        rc = mldsa_consume(path, iterations);
    } else if (strcmp(mode, "combined_gen") == 0) {
        rc = combined_gen(path, iterations);
    } else if (strcmp(mode, "combined_consume") == 0) {
        rc = combined_consume(path, iterations);
    } else {
        usage(argv[0]);
        rc = 2;
    }

    v33_workspace_free();

    return rc;
}
