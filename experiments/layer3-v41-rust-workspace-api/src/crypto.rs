use crate::ffi::*;
use crate::workspace::PqcWorkspaceContext;

use std::ffi::CString;
use std::sync::atomic::{AtomicU64, Ordering};

static RNG_STATE: AtomicU64 = AtomicU64::new(0x4141_4141_1234_5678);

pub struct CaseResult {
    pub name: &'static str,
    pub iterations: usize,
    pub passed: usize,
    pub failed: usize,
    pub notes: &'static str,
}

impl CaseResult {
    pub fn from_bool(name: &'static str, status: bool, notes: &'static str) -> Self {
        Self {
            name,
            iterations: 1,
            passed: usize::from(status),
            failed: usize::from(!status),
            notes,
        }
    }
}

unsafe extern "C" fn v41_randombytes(out: *mut u8, outlen: usize) {
    for index in 0..outlen {
        let random = xorshift64star();
        unsafe {
            *out.add(index) = (random >> ((index % 8) * 8)) as u8;
        }
    }
}

fn xorshift64star() -> u64 {
    let mut value = RNG_STATE.load(Ordering::Relaxed);

    value ^= value >> 12;
    value ^= value << 25;
    value ^= value >> 27;

    RNG_STATE.store(value, Ordering::Relaxed);

    value.wrapping_mul(0x2545_F491_4F6C_DD1D)
}

pub fn initialize() {
    unsafe {
        OQS_init();
        OQS_randombytes_custom_algorithm(Some(v41_randombytes));
    }
}

pub fn shutdown() {
    unsafe {
        OQS_destroy();
    }
}

struct KemHandle {
    ptr: *mut OQS_KEM,
}

impl KemHandle {
    fn new() -> Result<Self, String> {
        let name = CString::new("ML-KEM-768").expect("valid KEM name");
        let ptr = unsafe { OQS_KEM_new(name.as_ptr()) };

        if ptr.is_null() {
            return Err("OQS_KEM_new failed for ML-KEM-768".to_string());
        }

        Ok(Self { ptr })
    }

    fn kem(&self) -> &OQS_KEM {
        unsafe { &*self.ptr }
    }
}

impl Drop for KemHandle {
    fn drop(&mut self) {
        if !self.ptr.is_null() {
            unsafe {
                OQS_KEM_free(self.ptr);
            }
        }
    }
}

struct SigHandle {
    ptr: *mut OQS_SIG,
}

impl SigHandle {
    fn new() -> Result<Self, String> {
        let name = CString::new("ML-DSA-44").expect("valid signature name");
        let ptr = unsafe { OQS_SIG_new(name.as_ptr()) };

        if ptr.is_null() {
            return Err("OQS_SIG_new failed for ML-DSA-44".to_string());
        }

        Ok(Self { ptr })
    }

    fn sig(&self) -> &OQS_SIG {
        unsafe { &*self.ptr }
    }
}

impl Drop for SigHandle {
    fn drop(&mut self) {
        if !self.ptr.is_null() {
            unsafe {
                OQS_SIG_free(self.ptr);
            }
        }
    }
}

fn message_for_iteration(length: usize, iteration: usize, domain: u8) -> Vec<u8> {
    let mut message = vec![0u8; length];

    for (index, byte) in message.iter_mut().enumerate() {
        *byte = domain ^ (index as u8) ^ ((iteration * 131) as u8);
    }

    message
}

pub fn mlkem_flow(context: &mut PqcWorkspaceContext, iterations: usize) -> CaseResult {
    let kem = match KemHandle::new() {
        Ok(kem) => kem,
        Err(_) => {
            return CaseResult {
                name: "rust_workspace_api_mlkem_flow",
                iterations,
                passed: 0,
                failed: iterations,
                notes: "ML-KEM handle creation failed",
            }
        }
    };

    let lengths = kem.kem();

    let mut passed = 0usize;
    let mut failed = 0usize;

    for _ in 0..iterations {
        let mut public_key = vec![0u8; lengths.length_public_key];
        let mut secret_key = vec![0u8; lengths.length_secret_key];
        let mut ciphertext = vec![0u8; lengths.length_ciphertext];
        let mut shared_secret_a = vec![0u8; lengths.length_shared_secret];
        let mut shared_secret_b = vec![0u8; lengths.length_shared_secret];

        let result = context.with_active(|| unsafe {
            OQS_KEM_keypair(kem.ptr, public_key.as_mut_ptr(), secret_key.as_mut_ptr())
                == OQS_SUCCESS
                && OQS_KEM_encaps(
                    kem.ptr,
                    ciphertext.as_mut_ptr(),
                    shared_secret_a.as_mut_ptr(),
                    public_key.as_ptr(),
                ) == OQS_SUCCESS
                && OQS_KEM_decaps(
                    kem.ptr,
                    shared_secret_b.as_mut_ptr(),
                    ciphertext.as_ptr(),
                    secret_key.as_ptr(),
                ) == OQS_SUCCESS
                && shared_secret_a == shared_secret_b
        });

        if result.unwrap_or(false) {
            passed += 1;
        } else {
            failed += 1;
        }
    }

    CaseResult {
        name: "rust_workspace_api_mlkem_flow",
        iterations,
        passed,
        failed,
        notes: "ML-KEM flow through Rust workspace context",
    }
}

pub fn mldsa_flow(context: &mut PqcWorkspaceContext, iterations: usize) -> CaseResult {
    let sig = match SigHandle::new() {
        Ok(sig) => sig,
        Err(_) => {
            return CaseResult {
                name: "rust_workspace_api_mldsa_flow",
                iterations,
                passed: 0,
                failed: iterations,
                notes: "ML-DSA handle creation failed",
            }
        }
    };

    let lengths = sig.sig();

    let mut passed = 0usize;
    let mut failed = 0usize;

    for iteration in 0..iterations {
        let mut public_key = vec![0u8; lengths.length_public_key];
        let mut secret_key = vec![0u8; lengths.length_secret_key];
        let mut signature = vec![0u8; lengths.length_signature];
        let mut signature_len = 0usize;

        let message = message_for_iteration(96, iteration, 0x41);

        let result = context.with_active(|| unsafe {
            let keypair_ok =
                OQS_SIG_keypair(sig.ptr, public_key.as_mut_ptr(), secret_key.as_mut_ptr())
                    == OQS_SUCCESS;

            if !keypair_ok {
                return false;
            }

            let sign_ok = OQS_SIG_sign(
                sig.ptr,
                signature.as_mut_ptr(),
                &mut signature_len,
                message.as_ptr(),
                message.len(),
                secret_key.as_ptr(),
            ) == OQS_SUCCESS;

            if !sign_ok || signature_len > signature.len() {
                return false;
            }

            let valid_ok = OQS_SIG_verify(
                sig.ptr,
                message.as_ptr(),
                message.len(),
                signature.as_ptr(),
                signature_len,
                public_key.as_ptr(),
            ) == OQS_SUCCESS;

            let mut modified_message = message.clone();
            modified_message[0] ^= 0x01;

            let modified_message_rejected = OQS_SIG_verify(
                sig.ptr,
                modified_message.as_ptr(),
                modified_message.len(),
                signature.as_ptr(),
                signature_len,
                public_key.as_ptr(),
            ) != OQS_SUCCESS;

            let mut modified_signature = signature.clone();

            if signature_len > 0 {
                modified_signature[0] ^= 0x01;
            }

            let modified_signature_rejected = OQS_SIG_verify(
                sig.ptr,
                message.as_ptr(),
                message.len(),
                modified_signature.as_ptr(),
                signature_len,
                public_key.as_ptr(),
            ) != OQS_SUCCESS;

            valid_ok && modified_message_rejected && modified_signature_rejected
        });

        if result.unwrap_or(false) {
            passed += 1;
        } else {
            failed += 1;
        }
    }

    CaseResult {
        name: "rust_workspace_api_mldsa_flow",
        iterations,
        passed,
        failed,
        notes: "ML-DSA flow through Rust workspace context",
    }
}

pub fn combined_flow(context: &mut PqcWorkspaceContext, iterations: usize) -> CaseResult {
    let kem = match KemHandle::new() {
        Ok(kem) => kem,
        Err(_) => {
            return CaseResult {
                name: "rust_workspace_api_combined_flow",
                iterations,
                passed: 0,
                failed: iterations,
                notes: "ML-KEM handle creation failed",
            }
        }
    };

    let sig = match SigHandle::new() {
        Ok(sig) => sig,
        Err(_) => {
            return CaseResult {
                name: "rust_workspace_api_combined_flow",
                iterations,
                passed: 0,
                failed: iterations,
                notes: "ML-DSA handle creation failed",
            }
        }
    };

    let kem_lengths = kem.kem();
    let sig_lengths = sig.sig();

    let mut passed = 0usize;
    let mut failed = 0usize;

    for _ in 0..iterations {
        let mut kem_public_key = vec![0u8; kem_lengths.length_public_key];
        let mut kem_secret_key = vec![0u8; kem_lengths.length_secret_key];
        let mut ciphertext = vec![0u8; kem_lengths.length_ciphertext];
        let mut shared_secret_a = vec![0u8; kem_lengths.length_shared_secret];
        let mut shared_secret_b = vec![0u8; kem_lengths.length_shared_secret];

        let mut sig_public_key = vec![0u8; sig_lengths.length_public_key];
        let mut sig_secret_key = vec![0u8; sig_lengths.length_secret_key];
        let mut signature = vec![0u8; sig_lengths.length_signature];
        let mut signature_len = 0usize;

        let result = context.with_active(|| unsafe {
            let kem_ok = OQS_KEM_keypair(
                kem.ptr,
                kem_public_key.as_mut_ptr(),
                kem_secret_key.as_mut_ptr(),
            ) == OQS_SUCCESS
                && OQS_KEM_encaps(
                    kem.ptr,
                    ciphertext.as_mut_ptr(),
                    shared_secret_a.as_mut_ptr(),
                    kem_public_key.as_ptr(),
                ) == OQS_SUCCESS
                && OQS_KEM_decaps(
                    kem.ptr,
                    shared_secret_b.as_mut_ptr(),
                    ciphertext.as_ptr(),
                    kem_secret_key.as_ptr(),
                ) == OQS_SUCCESS
                && shared_secret_a == shared_secret_b;

            if !kem_ok {
                return false;
            }

            let mut transcript =
                Vec::with_capacity(kem_public_key.len() + ciphertext.len() + shared_secret_a.len());

            transcript.extend_from_slice(&kem_public_key);
            transcript.extend_from_slice(&ciphertext);
            transcript.extend_from_slice(&shared_secret_a);

            let sig_ok = OQS_SIG_keypair(
                sig.ptr,
                sig_public_key.as_mut_ptr(),
                sig_secret_key.as_mut_ptr(),
            ) == OQS_SUCCESS
                && OQS_SIG_sign(
                    sig.ptr,
                    signature.as_mut_ptr(),
                    &mut signature_len,
                    transcript.as_ptr(),
                    transcript.len(),
                    sig_secret_key.as_ptr(),
                ) == OQS_SUCCESS
                && signature_len <= signature.len()
                && OQS_SIG_verify(
                    sig.ptr,
                    transcript.as_ptr(),
                    transcript.len(),
                    signature.as_ptr(),
                    signature_len,
                    sig_public_key.as_ptr(),
                ) == OQS_SUCCESS;

            if !sig_ok {
                return false;
            }

            let mut modified_transcript = transcript.clone();
            modified_transcript[0] ^= 0x01;

            OQS_SIG_verify(
                sig.ptr,
                modified_transcript.as_ptr(),
                modified_transcript.len(),
                signature.as_ptr(),
                signature_len,
                sig_public_key.as_ptr(),
            ) != OQS_SUCCESS
        });

        if result.unwrap_or(false) {
            passed += 1;
        } else {
            failed += 1;
        }
    }

    CaseResult {
        name: "rust_workspace_api_combined_flow",
        iterations,
        passed,
        failed,
        notes: "Combined ML-KEM and ML-DSA flow through workspace context",
    }
}
