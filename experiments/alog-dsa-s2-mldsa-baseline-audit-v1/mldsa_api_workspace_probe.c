#include <oqs/oqs.h>

#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

extern size_t
PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes(void);

extern size_t
PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes(void);

int main(void)
{
    OQS_SIG *sig = OQS_SIG_new(OQS_SIG_alg_ml_dsa_44);

    if (sig == NULL) {
        fprintf(stderr, "ERROR,OQS_SIG_new,ML-DSA-44\n");
        return EXIT_FAILURE;
    }

    printf("AUDIT_METRIC,algorithm,%s\n",
           sig->method_name);

    printf("AUDIT_METRIC,public_key_bytes,%zu\n",
           sig->length_public_key);

    printf("AUDIT_METRIC,secret_key_bytes,%zu\n",
           sig->length_secret_key);

    printf("AUDIT_METRIC,signature_bytes,%zu\n",
           sig->length_signature);

    printf("AUDIT_METRIC,C_v24_lifecycle_workspace_bytes,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes());

    printf("AUDIT_METRIC,X86_64_v24_lifecycle_workspace_bytes,%zu\n",
           PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes());

    OQS_SIG_free(sig);

    return EXIT_SUCCESS;
}
