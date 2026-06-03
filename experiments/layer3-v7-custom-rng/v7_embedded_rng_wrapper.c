#include <oqs/oqs.h>

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <time.h>
#include <unistd.h>

#define KEM_ALG "ML-KEM-768"
#define SIG_ALG "ML-DSA-44"

static void custom_getrandom_rng(uint8_t *random_array, size_t bytes_to_read) {
    size_t offset = 0;

    while (offset < bytes_to_read) {
        ssize_t ret = getrandom(
            random_array + offset,
            bytes_to_read - offset,
            0
        );

        if (ret < 0) {
            if (errno == EINTR) {
                continue;
            }

            perror("getrandom failed");
            abort();
        }

        if (ret == 0) {
            fprintf(stderr, "getrandom returned 0 bytes\n");
            abort();
        }

        offset += (size_t) ret;
    }
}

static double elapsed_us(struct timespec start, struct timespec end) {
    double sec = (double)(end.tv_sec - start.tv_sec);
    double nsec = (double)(end.tv_nsec - start.tv_nsec);
    return (sec * 1000000.0) + (nsec / 1000.0);
}

static void *checked_calloc(size_t n, size_t size, const char *name) {
    void *ptr = calloc(n, size);
    if (ptr == NULL) {
        fprintf(stderr, "allocation failed: %s\n", name);
        exit(EXIT_FAILURE);
    }
    return ptr;
}

static int run_kem(size_t iterations) {
    OQS_KEM *kem = OQS_KEM_new(KEM_ALG);
    if (kem == NULL) {
        fprintf(stderr, "KEM not available: %s\n", KEM_ALG);
        return EXIT_FAILURE;
    }

    uint8_t *pk = checked_calloc(kem->length_public_key, 1, "kem public key");
    uint8_t *sk = checked_calloc(kem->length_secret_key, 1, "kem secret key");
    uint8_t *ct = checked_calloc(kem->length_ciphertext, 1, "kem ciphertext");
    uint8_t *ss1 = checked_calloc(kem->length_shared_secret, 1, "kem shared secret 1");
    uint8_t *ss2 = checked_calloc(kem->length_shared_secret, 1, "kem shared secret 2");

    struct timespec start, end;

    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM keypair failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_KEM_encaps(kem, ct, ss1, pk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM encaps failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_KEM_decaps(kem, ss2, ct, sk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM decaps failed\n");
        return EXIT_FAILURE;
    }

    if (memcmp(ss1, ss2, kem->length_shared_secret) != 0) {
        fprintf(stderr, "KEM shared secrets do not match\n");
        return EXIT_FAILURE;
    }

    clock_gettime(CLOCK_MONOTONIC, &start);
    for (size_t i = 0; i < iterations; i++) {
        if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
            fprintf(stderr, "KEM keypair failed during benchmark\n");
            return EXIT_FAILURE;
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    double keygen_us = elapsed_us(start, end) / (double) iterations;

    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM keypair failed before encaps benchmark\n");
        return EXIT_FAILURE;
    }

    clock_gettime(CLOCK_MONOTONIC, &start);
    for (size_t i = 0; i < iterations; i++) {
        if (OQS_KEM_encaps(kem, ct, ss1, pk) != OQS_SUCCESS) {
            fprintf(stderr, "KEM encaps failed during benchmark\n");
            return EXIT_FAILURE;
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    double encaps_us = elapsed_us(start, end) / (double) iterations;

    if (OQS_KEM_encaps(kem, ct, ss1, pk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM encaps failed before decaps benchmark\n");
        return EXIT_FAILURE;
    }

    clock_gettime(CLOCK_MONOTONIC, &start);
    for (size_t i = 0; i < iterations; i++) {
        if (OQS_KEM_decaps(kem, ss2, ct, sk) != OQS_SUCCESS) {
            fprintf(stderr, "KEM decaps failed during benchmark\n");
            return EXIT_FAILURE;
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    double decaps_us = elapsed_us(start, end) / (double) iterations;

    printf("KEM: %s\n", KEM_ALG);
    printf("iterations: %zu\n", iterations);
    printf("public_key_bytes: %zu\n", kem->length_public_key);
    printf("secret_key_bytes: %zu\n", kem->length_secret_key);
    printf("ciphertext_bytes: %zu\n", kem->length_ciphertext);
    printf("shared_secret_bytes: %zu\n", kem->length_shared_secret);
    printf("keygen_mean_us: %.3f\n", keygen_us);
    printf("encaps_mean_us: %.3f\n", encaps_us);
    printf("decaps_mean_us: %.3f\n", decaps_us);
    printf("correctness: shared secrets matched\n\n");

    free(pk);
    free(sk);
    free(ct);
    free(ss1);
    free(ss2);
    OQS_KEM_free(kem);

    return EXIT_SUCCESS;
}

static int run_sig(size_t iterations) {
    OQS_SIG *sig = OQS_SIG_new(SIG_ALG);
    if (sig == NULL) {
        fprintf(stderr, "SIG not available: %s\n", SIG_ALG);
        return EXIT_FAILURE;
    }

    const uint8_t message[] = "Layer 3 v7 embedded RNG wrapper benchmark";
    const size_t message_len = sizeof(message) - 1;

    uint8_t *pk = checked_calloc(sig->length_public_key, 1, "sig public key");
    uint8_t *sk = checked_calloc(sig->length_secret_key, 1, "sig secret key");
    uint8_t *signature = checked_calloc(sig->length_signature, 1, "signature");

    size_t signature_len = 0;
    struct timespec start, end;

    if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG keypair failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_SIG_sign(sig, signature, &signature_len, message, message_len, sk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG sign failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_SIG_verify(sig, message, message_len, signature, signature_len, pk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG verify failed\n");
        return EXIT_FAILURE;
    }

    clock_gettime(CLOCK_MONOTONIC, &start);
    for (size_t i = 0; i < iterations; i++) {
        if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
            fprintf(stderr, "SIG keypair failed during benchmark\n");
            return EXIT_FAILURE;
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    double keypair_us = elapsed_us(start, end) / (double) iterations;

    if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG keypair failed before sign benchmark\n");
        return EXIT_FAILURE;
    }

    clock_gettime(CLOCK_MONOTONIC, &start);
    for (size_t i = 0; i < iterations; i++) {
        if (OQS_SIG_sign(sig, signature, &signature_len, message, message_len, sk) != OQS_SUCCESS) {
            fprintf(stderr, "SIG sign failed during benchmark\n");
            return EXIT_FAILURE;
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    double sign_us = elapsed_us(start, end) / (double) iterations;

    if (OQS_SIG_sign(sig, signature, &signature_len, message, message_len, sk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG sign failed before verify benchmark\n");
        return EXIT_FAILURE;
    }

    clock_gettime(CLOCK_MONOTONIC, &start);
    for (size_t i = 0; i < iterations; i++) {
        if (OQS_SIG_verify(sig, message, message_len, signature, signature_len, pk) != OQS_SUCCESS) {
            fprintf(stderr, "SIG verify failed during benchmark\n");
            return EXIT_FAILURE;
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    double verify_us = elapsed_us(start, end) / (double) iterations;

    printf("SIG: %s\n", SIG_ALG);
    printf("iterations: %zu\n", iterations);
    printf("public_key_bytes: %zu\n", sig->length_public_key);
    printf("secret_key_bytes: %zu\n", sig->length_secret_key);
    printf("signature_max_bytes: %zu\n", sig->length_signature);
    printf("signature_actual_bytes: %zu\n", signature_len);
    printf("keypair_mean_us: %.3f\n", keypair_us);
    printf("sign_mean_us: %.3f\n", sign_us);
    printf("verify_mean_us: %.3f\n", verify_us);
    printf("correctness: signature verified\n\n");

    free(pk);
    free(sk);
    free(signature);
    OQS_SIG_free(sig);

    return EXIT_SUCCESS;
}

int main(int argc, char **argv) {
    size_t iterations = 10000;

    if (argc >= 2) {
        iterations = (size_t) strtoull(argv[1], NULL, 10);
        if (iterations == 0) {
            iterations = 10000;
        }
    }

    OQS_randombytes_custom_algorithm(custom_getrandom_rng);

    printf("Layer 3 v7 embedded custom RNG wrapper\n");
    printf("Build target: embedded minimal no-OpenSSL liboqs\n");
    printf("Custom RNG: Linux getrandom() test callback\n\n");

    if (run_kem(iterations) != EXIT_SUCCESS) {
        return EXIT_FAILURE;
    }

    if (run_sig(iterations) != EXIT_SUCCESS) {
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
