#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![allow(dead_code)]

use std::os::raw::{c_char, c_int};

pub type OQS_STATUS = c_int;

pub const OQS_SUCCESS: OQS_STATUS = 0;

#[repr(C)]
pub struct OQS_KEM {
    pub method_name: *const c_char,
    pub alg_version: *const c_char,
    pub claimed_nist_level: u8,
    pub ind_cca: bool,
    pub length_public_key: usize,
    pub length_secret_key: usize,
    pub length_ciphertext: usize,
    pub length_shared_secret: usize,
}

#[repr(C)]
pub struct OQS_SIG {
    pub method_name: *const c_char,
    pub alg_version: *const c_char,
    pub claimed_nist_level: u8,
    pub euf_cma: bool,
    pub sig_with_ctx_support: bool,
    pub length_public_key: usize,
    pub length_secret_key: usize,
    pub length_signature: usize,
}

extern "C" {
    pub fn OQS_init();
    pub fn OQS_destroy();

    pub fn OQS_randombytes_custom_algorithm(
        algorithm_ptr: Option<unsafe extern "C" fn(*mut u8, usize)>,
    );

    pub fn OQS_KEM_new(method_name: *const c_char) -> *mut OQS_KEM;
    pub fn OQS_KEM_free(kem: *mut OQS_KEM);

    pub fn OQS_KEM_keypair(
        kem: *const OQS_KEM,
        public_key: *mut u8,
        secret_key: *mut u8,
    ) -> OQS_STATUS;

    pub fn OQS_KEM_encaps(
        kem: *const OQS_KEM,
        ciphertext: *mut u8,
        shared_secret: *mut u8,
        public_key: *const u8,
    ) -> OQS_STATUS;

    pub fn OQS_KEM_decaps(
        kem: *const OQS_KEM,
        shared_secret: *mut u8,
        ciphertext: *const u8,
        secret_key: *const u8,
    ) -> OQS_STATUS;

    pub fn OQS_SIG_new(method_name: *const c_char) -> *mut OQS_SIG;
    pub fn OQS_SIG_free(sig: *mut OQS_SIG);

    pub fn OQS_SIG_keypair(
        sig: *const OQS_SIG,
        public_key: *mut u8,
        secret_key: *mut u8,
    ) -> OQS_STATUS;

    pub fn OQS_SIG_sign(
        sig: *const OQS_SIG,
        signature: *mut u8,
        signature_len: *mut usize,
        message: *const u8,
        message_len: usize,
        secret_key: *const u8,
    ) -> OQS_STATUS;

    pub fn OQS_SIG_verify(
        sig: *const OQS_SIG,
        message: *const u8,
        message_len: usize,
        signature: *const u8,
        signature_len: usize,
        public_key: *const u8,
    ) -> OQS_STATUS;

    pub fn PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes() -> usize;
    pub fn PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_set(
        ptr: *mut u8,
        len: usize,
    ) -> c_int;

    pub fn PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes() -> usize;
    pub fn PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_set(
        ptr: *mut u8,
        len: usize,
    ) -> c_int;

    pub fn PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes() -> usize;
    pub fn PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_set(
        ptr: *mut u8,
        len: usize,
    ) -> c_int;

    pub fn PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes() -> usize;
    pub fn PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_set(
        ptr: *mut u8,
        len: usize,
    ) -> c_int;
}
