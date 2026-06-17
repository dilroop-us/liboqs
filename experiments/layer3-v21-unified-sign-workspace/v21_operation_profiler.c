#define _GNU_SOURCE

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <time.h>

#include <oqs/oqs.h>

#define SIG_ALG OQS_SIG_alg_ml_dsa_44
#define MESSAGE_LEN 47

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes(void)
    __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_set(void *workspace,
                                                                    size_t workspace_bytes)
    __attribute__((weak));

extern size_t PQCP_MLDSA_NATIVE_MLDSA44_C_v21_sign_workspace_bytes(void)
    __attribute__((weak));
extern int PQCP_MLDSA_NATIVE_MLDSA44_C_v21_sign_workspace_set(void *workspace,
                                                              size_t workspace_bytes)
    __attribute__((weak));

static void *v21_x86_workspace;
static void *v21_c_workspace;

static void die(const char *msg) {
  fprintf(stderr, "%s\n", msg);
  exit(1);
}

static void linux_randombytes(uint8_t *out, size_t out_len) {
  size_t off = 0;

  while (off < out_len) {
    ssize_t got = getrandom(out + off, out_len - off, 0);

    if (got < 0) {
      if (errno == EINTR) {
        continue;
      }

      perror("getrandom");
      exit(1);
    }

    off += (size_t)got;
  }
}

static void *alloc_aligned(size_t bytes) {
  void *ptr = NULL;

  if (posix_memalign(&ptr, 64, bytes) != 0) {
    return NULL;
  }

  memset(ptr, 0, bytes);
  return ptr;
}

static void setup_v21_workspace_if_available(void) {
  if (PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_bytes();

    if (v21_x86_workspace == NULL) {
      v21_x86_workspace = alloc_aligned(bytes);
    }

    if (v21_x86_workspace == NULL ||
        PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v21_sign_workspace_set(
            v21_x86_workspace, bytes) != 0) {
      die("failed to setup v21 x86_64 unified workspace");
    }
  }

  if (PQCP_MLDSA_NATIVE_MLDSA44_C_v21_sign_workspace_bytes &&
      PQCP_MLDSA_NATIVE_MLDSA44_C_v21_sign_workspace_set) {
    size_t bytes = PQCP_MLDSA_NATIVE_MLDSA44_C_v21_sign_workspace_bytes();

    if (v21_c_workspace == NULL) {
      v21_c_workspace = alloc_aligned(bytes);
    }

    if (v21_c_workspace == NULL ||
        PQCP_MLDSA_NATIVE_MLDSA44_C_v21_sign_workspace_set(
            v21_c_workspace, bytes) != 0) {
      die("failed to setup v21 C unified workspace");
    }
  }
}

static double elapsed_us(struct timespec start, struct timespec end) {
  double sec = (double)(end.tv_sec - start.tv_sec);
  double nsec = (double)(end.tv_nsec - start.tv_nsec);

  return sec * 1000000.0 + nsec / 1000.0;
}

static void fill_message(uint8_t msg[MESSAGE_LEN]) {
  for (size_t i = 0; i < MESSAGE_LEN; i++) {
    msg[i] = (uint8_t)(0xA5u ^ (uint8_t)i);
  }
}

static void run_sig_sign(size_t iterations) {
  OQS_SIG *sig = OQS_SIG_new(SIG_ALG);
  setup_v21_workspace_if_available();

  if (sig == NULL) {
    die("OQS_SIG_new failed");
  }

  uint8_t *pk = malloc(sig->length_public_key);
  uint8_t *sk = malloc(sig->length_secret_key);
  uint8_t *signature = malloc(sig->length_signature);
  uint8_t message[MESSAGE_LEN];
  size_t sig_len = 0;

  if (pk == NULL || sk == NULL || signature == NULL) {
    die("malloc failed");
  }

  fill_message(message);

  if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
    die("keypair failed");
  }

  struct timespec start;
  struct timespec end;

  clock_gettime(CLOCK_MONOTONIC_RAW, &start);

  for (size_t i = 0; i < iterations; i++) {
    sig_len = 0;

    if (OQS_SIG_sign(sig, signature, &sig_len, message, MESSAGE_LEN, sk) != OQS_SUCCESS) {
      die("sign failed");
    }
  }

  clock_gettime(CLOCK_MONOTONIC_RAW, &end);

  if (OQS_SIG_verify(sig, message, MESSAGE_LEN, signature, sig_len, pk) != OQS_SUCCESS) {
    die("correctness verify failed");
  }

  printf("Layer 3 v21 unified sign workspace profiler\n");
  printf("Build target: embedded minimal no-OpenSSL liboqs\n");
  printf("Custom RNG: Linux getrandom() test callback\n\n");
  printf("mode: sig-sign\n");
  printf("algorithm: ML-DSA-44\n");
  printf("iterations: %zu\n", iterations);
  printf("secret_key_bytes: %zu\n", sig->length_secret_key);
  printf("signature_max_bytes: %zu\n", sig->length_signature);
  printf("signature_actual_bytes: %zu\n", sig_len);
  printf("message_bytes: %d\n", MESSAGE_LEN);
  printf("mean_us: %.3f\n", elapsed_us(start, end) / (double)iterations);
  printf("correctness: signature generated and verified\n");

  free(pk);
  free(sk);
  free(signature);
  OQS_SIG_free(sig);
}

static void run_sig_verify(size_t iterations) {
  OQS_SIG *sig = OQS_SIG_new(SIG_ALG);
  setup_v21_workspace_if_available();

  if (sig == NULL) {
    die("OQS_SIG_new failed");
  }

  uint8_t *pk = malloc(sig->length_public_key);
  uint8_t *sk = malloc(sig->length_secret_key);
  uint8_t *signature = malloc(sig->length_signature);
  uint8_t message[MESSAGE_LEN];
  size_t sig_len = 0;

  if (pk == NULL || sk == NULL || signature == NULL) {
    die("malloc failed");
  }

  fill_message(message);

  if (OQS_SIG_keypair(sig, pk, sk) != OQS_SUCCESS) {
    die("keypair failed");
  }

  if (OQS_SIG_sign(sig, signature, &sig_len, message, MESSAGE_LEN, sk) != OQS_SUCCESS) {
    die("sign failed");
  }

  struct timespec start;
  struct timespec end;

  clock_gettime(CLOCK_MONOTONIC_RAW, &start);

  for (size_t i = 0; i < iterations; i++) {
    if (OQS_SIG_verify(sig, message, MESSAGE_LEN, signature, sig_len, pk) != OQS_SUCCESS) {
      die("verify failed");
    }
  }

  clock_gettime(CLOCK_MONOTONIC_RAW, &end);

  printf("Layer 3 v21 unified sign workspace profiler\n");
  printf("Build target: embedded minimal no-OpenSSL liboqs\n");
  printf("Custom RNG: Linux getrandom() test callback\n\n");
  printf("mode: sig-verify\n");
  printf("algorithm: ML-DSA-44\n");
  printf("iterations: %zu\n", iterations);
  printf("public_key_bytes: %zu\n", sig->length_public_key);
  printf("signature_bytes: %zu\n", sig_len);
  printf("message_bytes: %d\n", MESSAGE_LEN);
  printf("mean_us: %.3f\n", elapsed_us(start, end) / (double)iterations);
  printf("correctness: signature verified\n");

  free(pk);
  free(sk);
  free(signature);
  OQS_SIG_free(sig);
}

int main(int argc, char **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: %s <sig-sign|sig-verify> <iterations>\n", argv[0]);
    return 2;
  }

  const char *mode = argv[1];
  size_t iterations = (size_t)strtoull(argv[2], NULL, 10);

  if (iterations == 0) {
    die("iterations must be > 0");
  }

  OQS_randombytes_custom_algorithm(linux_randombytes);

  if (strcmp(mode, "sig-sign") == 0) {
    run_sig_sign(iterations);
  } else if (strcmp(mode, "sig-verify") == 0) {
    run_sig_verify(iterations);
  } else {
    die("unknown mode");
  }

  return 0;
}
