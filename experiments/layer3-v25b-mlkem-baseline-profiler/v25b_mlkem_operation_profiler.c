#include <oqs/oqs.h>

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * Benchmark-only RNG for OQS_EMBEDDED_BUILD.
 *
 * This is NOT production randomness.
 * It is only used so the local profiler can run keypair/encaps/decaps
 * when liboqs is built with OQS_EMBEDDED_BUILD=ON.
 */
static uint64_t v25b_rng_state = 0x123456789abcdef0ull;

static uint64_t v25b_splitmix64(void) {
    uint64_t z = (v25b_rng_state += 0x9e3779b97f4a7c15ull);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
    return z ^ (z >> 31);
}

static void v25b_randombytes(uint8_t *out, size_t out_len) {
    size_t i = 0;

    while (i < out_len) {
        uint64_t r = v25b_splitmix64();

        for (size_t j = 0; j < 8 && i < out_len; j++, i++) {
            out[i] = (uint8_t)(r & 0xffu);
            r >>= 8;
        }
    }
}

#ifndef OQS_KEM_alg_ml_kem_768
#define OQS_KEM_alg_ml_kem_768 "ML-KEM-768"
#endif

static uint64_t now_ns(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {
        perror("clock_gettime");
        exit(1);
    }

    return ((uint64_t)ts.tv_sec * 1000000000ull) + (uint64_t)ts.tv_nsec;
}

static void die(const char *msg) {
    fprintf(stderr, "error: %s\n", msg);
    exit(1);
}

static void *xmalloc(size_t n) {
    void *p = malloc(n);

    if (p == NULL) {
        die("malloc failed");
    }

    memset(p, 0, n);
    return p;
}

static int file_is_empty_or_missing(const char *path) {
    FILE *f = fopen(path, "r");

    if (f == NULL) {
        return 1;
    }

    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return 1;
    }

    long size = ftell(f);
    fclose(f);

    return size <= 0;
}

static void append_csv(
    const char *path,
    const char *profile,
    const char *mode,
    uint64_t iterations,
    double mean_us,
    int ok
) {
    int need_header = file_is_empty_or_missing(path);

    FILE *f = fopen(path, "a");

    if (f == NULL) {
        perror("fopen");
        exit(1);
    }

    if (need_header) {
        fprintf(f, "profile,mode,iterations,mean_us,ok\n");
    }

    fprintf(
        f,
        "%s,%s,%" PRIu64 ",%.3f,%d\n",
        profile,
        mode,
        iterations,
        mean_us,
        ok
    );

    fclose(f);
}

static double bench_keypair(const OQS_KEM *kem, uint64_t iterations, int *ok_out) {
    uint8_t *pk = xmalloc(kem->length_public_key);
    uint8_t *sk = xmalloc(kem->length_secret_key);

    for (uint64_t i = 0; i < 100; i++) {
        if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
            *ok_out = 0;
            free(pk);
            free(sk);
            return 0.0;
        }
    }

    uint64_t start = now_ns();

    for (uint64_t i = 0; i < iterations; i++) {
        if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
            *ok_out = 0;
            free(pk);
            free(sk);
            return 0.0;
        }
    }

    uint64_t end = now_ns();

    free(pk);
    free(sk);

    *ok_out = 1;
    return (double)(end - start) / (double)iterations / 1000.0;
}

static double bench_encaps(const OQS_KEM *kem, uint64_t iterations, int *ok_out) {
    uint8_t *pk = xmalloc(kem->length_public_key);
    uint8_t *sk = xmalloc(kem->length_secret_key);
    uint8_t *ct = xmalloc(kem->length_ciphertext);
    uint8_t *ss = xmalloc(kem->length_shared_secret);

    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
        *ok_out = 0;
        goto cleanup;
    }

    for (uint64_t i = 0; i < 100; i++) {
        if (OQS_KEM_encaps(kem, ct, ss, pk) != OQS_SUCCESS) {
            *ok_out = 0;
            goto cleanup;
        }
    }

    uint64_t start = now_ns();

    for (uint64_t i = 0; i < iterations; i++) {
        if (OQS_KEM_encaps(kem, ct, ss, pk) != OQS_SUCCESS) {
            *ok_out = 0;
            goto cleanup;
        }
    }

    uint64_t end = now_ns();

    *ok_out = 1;

    free(pk);
    free(sk);
    free(ct);
    free(ss);

    return (double)(end - start) / (double)iterations / 1000.0;

cleanup:
    free(pk);
    free(sk);
    free(ct);
    free(ss);

    return 0.0;
}

static double bench_decaps(const OQS_KEM *kem, uint64_t iterations, int *ok_out) {
    uint8_t *pk = xmalloc(kem->length_public_key);
    uint8_t *sk = xmalloc(kem->length_secret_key);
    uint8_t *ct = xmalloc(kem->length_ciphertext);
    uint8_t *ss_enc = xmalloc(kem->length_shared_secret);
    uint8_t *ss_dec = xmalloc(kem->length_shared_secret);

    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
        *ok_out = 0;
        goto cleanup;
    }

    if (OQS_KEM_encaps(kem, ct, ss_enc, pk) != OQS_SUCCESS) {
        *ok_out = 0;
        goto cleanup;
    }

    if (OQS_KEM_decaps(kem, ss_dec, ct, sk) != OQS_SUCCESS) {
        *ok_out = 0;
        goto cleanup;
    }

    if (memcmp(ss_enc, ss_dec, kem->length_shared_secret) != 0) {
        *ok_out = 0;
        goto cleanup;
    }

    for (uint64_t i = 0; i < 100; i++) {
        if (OQS_KEM_decaps(kem, ss_dec, ct, sk) != OQS_SUCCESS) {
            *ok_out = 0;
            goto cleanup;
        }

        if (memcmp(ss_enc, ss_dec, kem->length_shared_secret) != 0) {
            *ok_out = 0;
            goto cleanup;
        }
    }

    uint64_t start = now_ns();

    for (uint64_t i = 0; i < iterations; i++) {
        if (OQS_KEM_decaps(kem, ss_dec, ct, sk) != OQS_SUCCESS) {
            *ok_out = 0;
            goto cleanup;
        }
    }

    uint64_t end = now_ns();

    if (memcmp(ss_enc, ss_dec, kem->length_shared_secret) != 0) {
        *ok_out = 0;
        goto cleanup;
    }

    *ok_out = 1;

    free(pk);
    free(sk);
    free(ct);
    free(ss_enc);
    free(ss_dec);

    return (double)(end - start) / (double)iterations / 1000.0;

cleanup:
    free(pk);
    free(sk);
    free(ct);
    free(ss_enc);
    free(ss_dec);

    return 0.0;
}

static uint64_t parse_iterations(const char *s) {
    char *end = NULL;
    errno = 0;

    unsigned long long value = strtoull(s, &end, 10);

    if (errno != 0 || end == s || *end != '\0' || value == 0) {
        die("invalid iterations");
    }

    return (uint64_t)value;
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(
            stderr,
            "usage: %s <profile> <iterations> <output-csv>\n",
            argv[0]
        );
        return 1;
    }

    const char *profile = argv[1];
    uint64_t iterations = parse_iterations(argv[2]);
    const char *out_csv = argv[3];

    OQS_randombytes_custom_algorithm(v25b_randombytes);

    OQS_KEM *kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);

    if (kem == NULL) {
        die("OQS_KEM_new failed for ML-KEM-768");
    }

    printf("profile=%s\n", profile);
    printf("algorithm=%s\n", kem->method_name);
    printf("public_key=%zu\n", kem->length_public_key);
    printf("secret_key=%zu\n", kem->length_secret_key);
    printf("ciphertext=%zu\n", kem->length_ciphertext);
    printf("shared_secret=%zu\n", kem->length_shared_secret);
    printf("iterations=%" PRIu64 "\n", iterations);

    int ok = 0;

    double keypair_us = bench_keypair(kem, iterations, &ok);
    append_csv(out_csv, profile, "kem-keypair", iterations, keypair_us, ok);
    printf("kem-keypair %.3f us ok=%d\n", keypair_us, ok);

    double encaps_us = bench_encaps(kem, iterations, &ok);
    append_csv(out_csv, profile, "kem-encaps", iterations, encaps_us, ok);
    printf("kem-encaps %.3f us ok=%d\n", encaps_us, ok);

    double decaps_us = bench_decaps(kem, iterations, &ok);
    append_csv(out_csv, profile, "kem-decaps", iterations, decaps_us, ok);
    printf("kem-decaps %.3f us ok=%d\n", decaps_us, ok);

    OQS_KEM_free(kem);

    return 0;
}
