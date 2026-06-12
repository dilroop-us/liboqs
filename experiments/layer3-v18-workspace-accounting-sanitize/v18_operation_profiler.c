#include <oqs/oqs.h>

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <time.h>

/*
 * v17b caller-provided full signing workspace integration.
 *
 * These symbols only exist in the v17b liboqs build.
 * They are weak so this profiler can still link against baseline,
 * reduced-RAM, v15, and v16 libraries.
 */
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes(void) __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_set(void *workspace, size_t workspace_bytes) __attribute__((weak));

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_bytes(void) __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_set(void *workspace, size_t workspace_bytes) __attribute__((weak));

static void *v17b_x86_workspace = 0;
static void *v17b_ref_workspace = 0;

static void *v17b_alloc_aligned(size_t bytes) {
  void *ptr = 0;
  if (posix_memalign(&ptr, 64, bytes) != 0) {
    return 0;
  }
  return ptr;
}

static void v17b_setup_workspace_if_available(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_bytes();

    if (v17b_x86_workspace == 0) {
      v17b_x86_workspace = v17b_alloc_aligned(bytes);
      if (v17b_x86_workspace == 0) {
        fprintf(stderr, "failed to allocate v17b x86_64 signing workspace\n");
        exit(1);
      }
    }

    if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v17b_sign_workspace_set(v17b_x86_workspace, bytes) != 0) {
      fprintf(stderr, "failed to set v17b x86_64 signing workspace\n");
      exit(1);
    }
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_bytes();

    if (v17b_ref_workspace == 0) {
      v17b_ref_workspace = v17b_alloc_aligned(bytes);
      if (v17b_ref_workspace == 0) {
        fprintf(stderr, "failed to allocate v17b ref signing workspace\n");
        exit(1);
      }
    }

    if (PQCP_MLDSA_NATIVE_MLDSA44_C_v17b_sign_workspace_set(v17b_ref_workspace, bytes) != 0) {
      fprintf(stderr, "failed to set v17b ref signing workspace\n");
      exit(1);
    }
  }
}



/*
 * v16 caller-provided workspace integration.
 *
 * These symbols only exist in the v16 liboqs build.
 * They are weak so the same profiler source can still link against
 * baseline and reduced-RAM libraries.
 */
extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes(void) __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_set(void *workspace, size_t workspace_bytes) __attribute__((weak));

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_bytes(void) __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_set(void *workspace, size_t workspace_bytes) __attribute__((weak));

static void *v16_x86_workspace = 0;
static void *v16_ref_workspace = 0;

static void *v16_alloc_aligned(size_t bytes) {
  void *ptr = 0;
  if (posix_memalign(&ptr, 64, bytes) != 0) {
    return 0;
  }
  return ptr;
}

static void v16_setup_workspace_if_available(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_bytes();

    if (v16_x86_workspace == 0) {
      v16_x86_workspace = v16_alloc_aligned(bytes);
      if (v16_x86_workspace == 0) {
        fprintf(stderr, "failed to allocate v16 x86_64 workspace\n");
        exit(1);
      }
    }

    if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v16_matrix_workspace_set(v16_x86_workspace, bytes) != 0) {
      fprintf(stderr, "failed to set v16 x86_64 workspace\n");
      exit(1);
    }
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_bytes();

    if (v16_ref_workspace == 0) {
      v16_ref_workspace = v16_alloc_aligned(bytes);
      if (v16_ref_workspace == 0) {
        fprintf(stderr, "failed to allocate v16 ref workspace\n");
        exit(1);
      }
    }

    if (PQCP_MLDSA_NATIVE_MLDSA44_C_v16_matrix_workspace_set(v16_ref_workspace, bytes) != 0) {
      fprintf(stderr, "failed to set v16 ref workspace\n");
      exit(1);
    }
  }
}



#define KEM_ALG "ML-KEM-768"
#define SIG_ALG "ML-DSA-44"

static void custom_getrandom_rng(uint8_t *random_array, size_t bytes_to_read) {
    size_t offset = 0;

    while (offset < bytes_to_read) {
        ssize_t ret = getrandom(random_array + offset, bytes_to_read - offset, 0);

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

static void *checked_calloc(size_t n, size_t size, const char *name) {
    void *ptr = calloc(n, size);

    if (ptr == NULL) {
        fprintf(stderr, "allocation failed: %s\n", name);
        exit(EXIT_FAILURE);
    }

    return ptr;
}

static double elapsed_us(struct timespec start, struct timespec end) {
    double sec = (double)(end.tv_sec - start.tv_sec);
    double nsec = (double)(end.tv_nsec - start.tv_nsec);
    return (sec * 1000000.0) + (nsec / 1000.0);
}

static void print_usage(const char *program_name) {
    fprintf(stderr, "Usage: %s <mode> [iterations]\n\n", program_name);
    fprintf(stderr, "Modes:\n");
    fprintf(stderr, "  kem-keygen\n");
    fprintf(stderr, "  kem-encaps\n");
    fprintf(stderr, "  kem-decaps\n");
    fprintf(stderr, "  sig-keypair\n");
    fprintf(stderr, "  sig-sign\n");
    fprintf(stderr, "  sig-verify\n\n");
    fprintf(stderr, "Example:\n");
    fprintf(stderr, "  %s sig-sign 50000\n", program_name);
}

static int run_kem_keygen(size_t iterations) {
    OQS_KEM *kem = OQS_KEM_new(KEM_ALG);
    if (kem == NULL) {
        fprintf(stderr, "KEM not available: %s\n", KEM_ALG);
        return EXIT_FAILURE;
    }

    uint8_t *pk = checked_calloc(kem->length_public_key, 1, "kem public key");
    uint8_t *sk = checked_calloc(kem->length_secret_key, 1, "kem secret key");

    struct timespec start;
    struct timespec end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for (size_t i = 0; i < iterations; i++) {
        if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
            fprintf(stderr, "KEM keygen failed\n");
            return EXIT_FAILURE;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    double mean_us = elapsed_us(start, end) / (double) iterations;

    printf("mode: kem-keygen\n");
    printf("algorithm: %s\n", KEM_ALG);
    printf("iterations: %zu\n", iterations);
    printf("public_key_bytes: %zu\n", kem->length_public_key);
    printf("secret_key_bytes: %zu\n", kem->length_secret_key);
    printf("mean_us: %.3f\n", mean_us);
    printf("correctness: operation completed\n");

    free(pk);
    free(sk);
    OQS_KEM_free(kem);

    return EXIT_SUCCESS;
}

static int run_kem_encaps(size_t iterations) {
    OQS_KEM *kem = OQS_KEM_new(KEM_ALG);
    if (kem == NULL) {
        fprintf(stderr, "KEM not available: %s\n", KEM_ALG);
        return EXIT_FAILURE;
    }

    uint8_t *pk = checked_calloc(kem->length_public_key, 1, "kem public key");
    uint8_t *sk = checked_calloc(kem->length_secret_key, 1, "kem secret key");
    uint8_t *ct = checked_calloc(kem->length_ciphertext, 1, "kem ciphertext");
    uint8_t *ss = checked_calloc(kem->length_shared_secret, 1, "kem shared secret");

    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM setup keygen failed\n");
        return EXIT_FAILURE;
    }

    struct timespec start;
    struct timespec end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for (size_t i = 0; i < iterations; i++) {
        if (OQS_KEM_encaps(kem, ct, ss, pk) != OQS_SUCCESS) {
            fprintf(stderr, "KEM encaps failed\n");
            return EXIT_FAILURE;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    double mean_us = elapsed_us(start, end) / (double) iterations;

    printf("mode: kem-encaps\n");
    printf("algorithm: %s\n", KEM_ALG);
    printf("iterations: %zu\n", iterations);
    printf("public_key_bytes: %zu\n", kem->length_public_key);
    printf("ciphertext_bytes: %zu\n", kem->length_ciphertext);
    printf("shared_secret_bytes: %zu\n", kem->length_shared_secret);
    printf("mean_us: %.3f\n", mean_us);
    printf("correctness: operation completed\n");

    free(pk);
    free(sk);
    free(ct);
    free(ss);
    OQS_KEM_free(kem);

    return EXIT_SUCCESS;
}

static int run_kem_decaps(size_t iterations) {
    OQS_KEM *kem = OQS_KEM_new(KEM_ALG);
    if (kem == NULL) {
        fprintf(stderr, "KEM not available: %s\n", KEM_ALG);
        return EXIT_FAILURE;
    }

    uint8_t *pk = checked_calloc(kem->length_public_key, 1, "kem public key");
    uint8_t *sk = checked_calloc(kem->length_secret_key, 1, "kem secret key");
    uint8_t *ct = checked_calloc(kem->length_ciphertext, 1, "kem ciphertext");
    uint8_t *ss_enc = checked_calloc(kem->length_shared_secret, 1, "kem shared secret enc");
    uint8_t *ss_dec = checked_calloc(kem->length_shared_secret, 1, "kem shared secret dec");

    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM setup keygen failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_KEM_encaps(kem, ct, ss_enc, pk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM setup encaps failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_KEM_decaps(kem, ss_dec, ct, sk) != OQS_SUCCESS) {
        fprintf(stderr, "KEM setup decaps failed\n");
        return EXIT_FAILURE;
    }

    if (memcmp(ss_enc, ss_dec, kem->length_shared_secret) != 0) {
        fprintf(stderr, "KEM setup shared secrets do not match\n");
        return EXIT_FAILURE;
    }

    struct timespec start;
    struct timespec end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for (size_t i = 0; i < iterations; i++) {
        if (OQS_KEM_decaps(kem, ss_dec, ct, sk) != OQS_SUCCESS) {
            fprintf(stderr, "KEM decaps failed\n");
            return EXIT_FAILURE;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    double mean_us = elapsed_us(start, end) / (double) iterations;

    printf("mode: kem-decaps\n");
    printf("algorithm: %s\n", KEM_ALG);
    printf("iterations: %zu\n", iterations);
    printf("secret_key_bytes: %zu\n", kem->length_secret_key);
    printf("ciphertext_bytes: %zu\n", kem->length_ciphertext);
    printf("shared_secret_bytes: %zu\n", kem->length_shared_secret);
    printf("mean_us: %.3f\n", mean_us);
    printf("correctness: shared secrets matched\n");

    free(pk);
    free(sk);
    free(ct);
    free(ss_enc);
    free(ss_dec);
    OQS_KEM_free(kem);

    return EXIT_SUCCESS;
}

static int run_sig_keypair(size_t iterations) {
    OQS_SIG *sig = OQS_SIG_new(SIG_ALG);
  v17b_setup_workspace_if_available();
  v16_setup_workspace_if_available();
    if (sig == NULL) {
        fprintf(stderr, "SIG not available: %s\n", SIG_ALG);
        return EXIT_FAILURE;
    }

    uint8_t *pk = checked_calloc(sig->length_public_key, 1, "sig public key");
    uint8_t *sk = checked_calloc(sig->length_secret_key, 1, "sig secret key");

    struct timespec start;
    struct timespec end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for (size_t i = 0; i < iterations; i++) {
        if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
            fprintf(stderr, "SIG keypair failed\n");
            return EXIT_FAILURE;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    double mean_us = elapsed_us(start, end) / (double) iterations;

    printf("mode: sig-keypair\n");
    printf("algorithm: %s\n", SIG_ALG);
    printf("iterations: %zu\n", iterations);
    printf("public_key_bytes: %zu\n", sig->length_public_key);
    printf("secret_key_bytes: %zu\n", sig->length_secret_key);
    printf("mean_us: %.3f\n", mean_us);
    printf("correctness: operation completed\n");

    free(pk);
    free(sk);
    OQS_SIG_free(sig);

    return EXIT_SUCCESS;
}

static int run_sig_sign(size_t iterations) {
    OQS_SIG *sig = OQS_SIG_new(SIG_ALG);
  v17b_setup_workspace_if_available();
  v16_setup_workspace_if_available();
    if (sig == NULL) {
        fprintf(stderr, "SIG not available: %s\n", SIG_ALG);
        return EXIT_FAILURE;
    }

    const uint8_t message[] = "Layer 3 v8 operation-specific profiling message";
    const size_t message_len = sizeof(message) - 1;

    uint8_t *pk = checked_calloc(sig->length_public_key, 1, "sig public key");
    uint8_t *sk = checked_calloc(sig->length_secret_key, 1, "sig secret key");
    uint8_t *signature = checked_calloc(sig->length_signature, 1, "signature");
    size_t signature_len = 0;

    if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG setup keypair failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_SIG_sign(sig, signature, &signature_len, message, message_len, sk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG setup sign failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_SIG_verify(sig, message, message_len, signature, signature_len, pk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG setup verify failed\n");
        return EXIT_FAILURE;
    }

    struct timespec start;
    struct timespec end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for (size_t i = 0; i < iterations; i++) {
        if (OQS_SIG_sign(sig, signature, &signature_len, message, message_len, sk) != OQS_SUCCESS) {
            fprintf(stderr, "SIG sign failed\n");
            return EXIT_FAILURE;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    double mean_us = elapsed_us(start, end) / (double) iterations;

    printf("mode: sig-sign\n");
    printf("algorithm: %s\n", SIG_ALG);
    printf("iterations: %zu\n", iterations);
    printf("secret_key_bytes: %zu\n", sig->length_secret_key);
    printf("signature_max_bytes: %zu\n", sig->length_signature);
    printf("signature_actual_bytes: %zu\n", signature_len);
    printf("message_bytes: %zu\n", message_len);
    printf("mean_us: %.3f\n", mean_us);
    printf("correctness: signature generated and verified\n");

    free(pk);
    free(sk);
    free(signature);
    OQS_SIG_free(sig);

    return EXIT_SUCCESS;
}

static int run_sig_verify(size_t iterations) {
    OQS_SIG *sig = OQS_SIG_new(SIG_ALG);
  v17b_setup_workspace_if_available();
  v16_setup_workspace_if_available();
    if (sig == NULL) {
        fprintf(stderr, "SIG not available: %s\n", SIG_ALG);
        return EXIT_FAILURE;
    }

    const uint8_t message[] = "Layer 3 v8 operation-specific profiling message";
    const size_t message_len = sizeof(message) - 1;

    uint8_t *pk = checked_calloc(sig->length_public_key, 1, "sig public key");
    uint8_t *sk = checked_calloc(sig->length_secret_key, 1, "sig secret key");
    uint8_t *signature = checked_calloc(sig->length_signature, 1, "signature");
    size_t signature_len = 0;

    if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG setup keypair failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_SIG_sign(sig, signature, &signature_len, message, message_len, sk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG setup sign failed\n");
        return EXIT_FAILURE;
    }

    if (OQS_SIG_verify(sig, message, message_len, signature, signature_len, pk) != OQS_SUCCESS) {
        fprintf(stderr, "SIG setup verify failed\n");
        return EXIT_FAILURE;
    }

    struct timespec start;
    struct timespec end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    for (size_t i = 0; i < iterations; i++) {
        if (OQS_SIG_verify(sig, message, message_len, signature, signature_len, pk) != OQS_SUCCESS) {
            fprintf(stderr, "SIG verify failed\n");
            return EXIT_FAILURE;
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end);

    double mean_us = elapsed_us(start, end) / (double) iterations;

    printf("mode: sig-verify\n");
    printf("algorithm: %s\n", SIG_ALG);
    printf("iterations: %zu\n", iterations);
    printf("public_key_bytes: %zu\n", sig->length_public_key);
    printf("signature_bytes: %zu\n", signature_len);
    printf("message_bytes: %zu\n", message_len);
    printf("mean_us: %.3f\n", mean_us);
    printf("correctness: signature verified\n");

    free(pk);
    free(sk);
    free(signature);
    OQS_SIG_free(sig);

    return EXIT_SUCCESS;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        print_usage(argv[0]);
        return EXIT_FAILURE;
    }

    const char *mode = argv[1];

    size_t iterations = 10000;
    if (argc >= 3) {
        iterations = (size_t) strtoull(argv[2], NULL, 10);
        if (iterations == 0) {
            iterations = 10000;
        }
    }

    OQS_randombytes_custom_algorithm(custom_getrandom_rng);

    printf("Layer 3 v18 workspace accounting and sanitize profiler\n");
    printf("Build target: embedded minimal no-OpenSSL liboqs\n");
    printf("Custom RNG: Linux getrandom() test callback\n\n");

    if (strcmp(mode, "kem-keygen") == 0) {
        return run_kem_keygen(iterations);
    }

    if (strcmp(mode, "kem-encaps") == 0) {
        return run_kem_encaps(iterations);
    }

    if (strcmp(mode, "kem-decaps") == 0) {
        return run_kem_decaps(iterations);
    }

    if (strcmp(mode, "sig-keypair") == 0) {
        return run_sig_keypair(iterations);
    }

    if (strcmp(mode, "sig-sign") == 0) {
        return run_sig_sign(iterations);
    }

    if (strcmp(mode, "sig-verify") == 0) {
        return run_sig_verify(iterations);
    }

    fprintf(stderr, "Unknown mode: %s\n\n", mode);
    print_usage(argv[0]);

    return EXIT_FAILURE;
}
