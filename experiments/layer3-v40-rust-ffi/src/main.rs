mod ffi;

use ffi::*;
use std::alloc::{alloc_zeroed, dealloc, Layout};
use std::env;
use std::ffi::CString;
use std::ptr;
use std::sync::atomic::{AtomicU64, Ordering};

static RNG_STATE: AtomicU64 = AtomicU64::new(0x4040_4040_1234_5678);

unsafe extern "C" fn v40_randombytes(out: *mut u8, outlen: usize) {
    for i in 0..outlen {
        let r = xorshift64star();
        *out.add(i) = (r >> ((i % 8) * 8)) as u8;
    }
}

fn xorshift64star() -> u64 {
    let mut x = RNG_STATE.load(Ordering::Relaxed);
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    RNG_STATE.store(x, Ordering::Relaxed);
    x.wrapping_mul(0x2545_F491_4F6C_DD1D)
}

struct AlignedWorkspace {
    ptr: *mut u8,
    len: usize,
    layout: Layout,
}

impl AlignedWorkspace {
    fn new(len: usize, alignment: usize) -> Self {
        let layout = Layout::from_size_align(len, alignment)
            .expect("invalid aligned workspace layout");

        let ptr = unsafe { alloc_zeroed(layout) };

        if ptr.is_null() {
            panic!("aligned workspace allocation failed for {len} bytes");
        }

        Self { ptr, len, layout }
    }

    fn as_mut_ptr(&mut self) -> *mut u8 {
        self.ptr
    }
}

impl Drop for AlignedWorkspace {
    fn drop(&mut self) {
        if !self.ptr.is_null() {
            unsafe {
                ptr::write_bytes(self.ptr, 0, self.len);
                dealloc(self.ptr, self.layout);
            }
        }
    }
}

struct KemHandle {
    ptr: *mut OQS_KEM,
}

impl KemHandle {
    fn new(name: &str) -> Result<Self, String> {
        let cname = CString::new(name).unwrap();
        let ptr = unsafe { OQS_KEM_new(cname.as_ptr()) };

        if ptr.is_null() {
            return Err(format!("OQS_KEM_new failed for {name}"));
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
            unsafe { OQS_KEM_free(self.ptr) };
        }
    }
}

struct SigHandle {
    ptr: *mut OQS_SIG,
}

impl SigHandle {
    fn new(name: &str) -> Result<Self, String> {
        let cname = CString::new(name).unwrap();
        let ptr = unsafe { OQS_SIG_new(cname.as_ptr()) };

        if ptr.is_null() {
            return Err(format!("OQS_SIG_new failed for {name}"));
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
            unsafe { OQS_SIG_free(self.ptr) };
        }
    }
}

fn mlkem_workspace_need() -> usize {
    unsafe {
        let c = PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes();
        let x86 = PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes();
        c.max(x86)
    }
}

fn mldsa_workspace_need() -> usize {
    unsafe {
        let c = PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes();
        let x86 = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes();
        c.max(x86)
    }
}

fn set_mlkem_workspace(ws: &mut AlignedWorkspace) -> Result<(), String> {
    let mut ok = false;

    unsafe {
        let c_len = PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes();
        let x86_len = PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes();

        if PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_set(ws.as_mut_ptr(), c_len) == 0 {
            ok = true;
        }

        if PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_set(ws.as_mut_ptr(), x86_len) == 0 {
            ok = true;
        }
    }

    if ok {
        Ok(())
    } else {
        Err("ML-KEM workspace setter failed for all implementations".to_string())
    }
}

fn set_mldsa_workspace(ws: &mut AlignedWorkspace) -> Result<(), String> {
    let mut ok = false;

    unsafe {
        let c_len = PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes();
        let x86_len = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes();

        if PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_set(ws.as_mut_ptr(), c_len) == 0 {
            ok = true;
        }

        if PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_set(ws.as_mut_ptr(), x86_len) == 0 {
            ok = true;
        }
    }

    if ok {
        Ok(())
    } else {
        Err("ML-DSA workspace setter failed for all implementations".to_string())
    }
}

fn fill_message(len: usize, iter: usize, domain: u8) -> Vec<u8> {
    let mut m = vec![0u8; len];

    for (i, b) in m.iter_mut().enumerate() {
        *b = domain ^ (i as u8) ^ ((iter * 131) as u8);
    }

    m
}

fn mlkem_valid_flow(iterations: usize) -> (usize, usize, String) {
    let kem = match KemHandle::new("ML-KEM-768") {
        Ok(k) => k,
        Err(e) => return (0, iterations, e),
    };

    let k = kem.kem();

    let mut passed = 0usize;
    let mut failed = 0usize;

    for _ in 0..iterations {
        let mut pk = vec![0u8; k.length_public_key];
        let mut sk = vec![0u8; k.length_secret_key];
        let mut ct = vec![0u8; k.length_ciphertext];
        let mut ss1 = vec![0u8; k.length_shared_secret];
        let mut ss2 = vec![0u8; k.length_shared_secret];

        let ok = unsafe {
            OQS_KEM_keypair(kem.ptr, pk.as_mut_ptr(), sk.as_mut_ptr()) == OQS_SUCCESS
                && OQS_KEM_encaps(kem.ptr, ct.as_mut_ptr(), ss1.as_mut_ptr(), pk.as_ptr()) == OQS_SUCCESS
                && OQS_KEM_decaps(kem.ptr, ss2.as_mut_ptr(), ct.as_ptr(), sk.as_ptr()) == OQS_SUCCESS
                && ss1 == ss2
        };

        if ok {
            passed += 1;
        } else {
            failed += 1;
        }
    }

    (passed, failed, "Rust FFI ML-KEM keypair/encaps/decaps/shared-secret equality".to_string())
}

fn mldsa_valid_and_negative(iterations: usize) -> (usize, usize, String) {
    let sig = match SigHandle::new("ML-DSA-44") {
        Ok(s) => s,
        Err(e) => return (0, iterations, e),
    };

    let s = sig.sig();

    let mut passed = 0usize;
    let mut failed = 0usize;

    for i in 0..iterations {
        let mut pk = vec![0u8; s.length_public_key];
        let mut sk = vec![0u8; s.length_secret_key];
        let msg = fill_message(96, i, 0x40);

        let mut sigbuf = vec![0u8; s.length_signature];
        let mut siglen: usize = 0;

        let mut ok = unsafe {
            OQS_SIG_keypair(sig.ptr, pk.as_mut_ptr(), sk.as_mut_ptr()) == OQS_SUCCESS
                && OQS_SIG_sign(
                    sig.ptr,
                    sigbuf.as_mut_ptr(),
                    &mut siglen as *mut usize,
                    msg.as_ptr(),
                    msg.len(),
                    sk.as_ptr(),
                ) == OQS_SUCCESS
                && siglen <= sigbuf.len()
                && OQS_SIG_verify(
                    sig.ptr,
                    msg.as_ptr(),
                    msg.len(),
                    sigbuf.as_ptr(),
                    siglen,
                    pk.as_ptr(),
                ) == OQS_SUCCESS
        };

        let mut modified_msg = msg.clone();
        modified_msg[0] ^= 0x01;

        let reject_modified_msg = unsafe {
            OQS_SIG_verify(
                sig.ptr,
                modified_msg.as_ptr(),
                modified_msg.len(),
                sigbuf.as_ptr(),
                siglen,
                pk.as_ptr(),
            ) != OQS_SUCCESS
        };

        let mut modified_sig = sigbuf.clone();
        if siglen > 0 {
            modified_sig[0] ^= 0x01;
        }

        let reject_modified_sig = unsafe {
            OQS_SIG_verify(
                sig.ptr,
                msg.as_ptr(),
                msg.len(),
                modified_sig.as_ptr(),
                siglen,
                pk.as_ptr(),
            ) != OQS_SUCCESS
        };

        ok = ok && reject_modified_msg && reject_modified_sig;

        if ok {
            passed += 1;
        } else {
            failed += 1;
        }
    }

    (passed, failed, "Rust FFI ML-DSA sign/verify plus modified message/signature rejection".to_string())
}

fn combined_mlkem_mldsa_sequence(iterations: usize) -> (usize, usize, String) {
    let kem = match KemHandle::new("ML-KEM-768") {
        Ok(k) => k,
        Err(e) => return (0, iterations, e),
    };

    let sig = match SigHandle::new("ML-DSA-44") {
        Ok(s) => s,
        Err(e) => return (0, iterations, e),
    };

    let k = kem.kem();
    let s = sig.sig();

    let mut passed = 0usize;
    let mut failed = 0usize;

    for _ in 0..iterations {
        let mut kem_pk = vec![0u8; k.length_public_key];
        let mut kem_sk = vec![0u8; k.length_secret_key];
        let mut ct = vec![0u8; k.length_ciphertext];
        let mut ss1 = vec![0u8; k.length_shared_secret];
        let mut ss2 = vec![0u8; k.length_shared_secret];

        let kem_ok = unsafe {
            OQS_KEM_keypair(kem.ptr, kem_pk.as_mut_ptr(), kem_sk.as_mut_ptr()) == OQS_SUCCESS
                && OQS_KEM_encaps(kem.ptr, ct.as_mut_ptr(), ss1.as_mut_ptr(), kem_pk.as_ptr()) == OQS_SUCCESS
                && OQS_KEM_decaps(kem.ptr, ss2.as_mut_ptr(), ct.as_ptr(), kem_sk.as_ptr()) == OQS_SUCCESS
                && ss1 == ss2
        };

        let mut transcript = Vec::with_capacity(kem_pk.len() + ct.len() + ss1.len());
        transcript.extend_from_slice(&kem_pk);
        transcript.extend_from_slice(&ct);
        transcript.extend_from_slice(&ss1);

        let mut sig_pk = vec![0u8; s.length_public_key];
        let mut sig_sk = vec![0u8; s.length_secret_key];
        let mut sigbuf = vec![0u8; s.length_signature];
        let mut siglen: usize = 0;

        let sig_ok = unsafe {
            OQS_SIG_keypair(sig.ptr, sig_pk.as_mut_ptr(), sig_sk.as_mut_ptr()) == OQS_SUCCESS
                && OQS_SIG_sign(
                    sig.ptr,
                    sigbuf.as_mut_ptr(),
                    &mut siglen as *mut usize,
                    transcript.as_ptr(),
                    transcript.len(),
                    sig_sk.as_ptr(),
                ) == OQS_SUCCESS
                && siglen <= sigbuf.len()
                && OQS_SIG_verify(
                    sig.ptr,
                    transcript.as_ptr(),
                    transcript.len(),
                    sigbuf.as_ptr(),
                    siglen,
                    sig_pk.as_ptr(),
                ) == OQS_SUCCESS
        };

        let mut modified_transcript = transcript.clone();
        modified_transcript[0] ^= 0x01;

        let reject_modified_transcript = unsafe {
            OQS_SIG_verify(
                sig.ptr,
                modified_transcript.as_ptr(),
                modified_transcript.len(),
                sigbuf.as_ptr(),
                siglen,
                sig_pk.as_ptr(),
            ) != OQS_SUCCESS
        };

        if kem_ok && sig_ok && reject_modified_transcript {
            passed += 1;
        } else {
            failed += 1;
        }
    }

    (passed, failed, "Rust FFI combined ML-KEM transcript plus ML-DSA signature flow".to_string())
}

fn print_case(name: &str, iterations: usize, passed: usize, failed: usize, notes: &str) {
    let status = if failed == 0 && passed == iterations {
        "PASS"
    } else {
        "FAIL"
    };

    println!(
        "V40_CASE,{},{},{},{},{},{}",
        name, iterations, passed, failed, status, notes
    );
}

fn main() {
    let iterations: usize = env::var("V40_ITERATIONS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(100);

    unsafe {
        OQS_init();
        OQS_randombytes_custom_algorithm(Some(v40_randombytes));
    }

    let mlkem_ws = mlkem_workspace_need();
    let mldsa_ws = mldsa_workspace_need();
    let combined_ws = mlkem_ws + mldsa_ws;

    let mut mlkem_workspace = AlignedWorkspace::new(mlkem_ws, 64);
    let mut mldsa_workspace = AlignedWorkspace::new(mldsa_ws, 64);

    let workspace_ok = set_mlkem_workspace(&mut mlkem_workspace)
        .and_then(|_| set_mldsa_workspace(&mut mldsa_workspace));

    if let Err(e) = workspace_ok {
        println!("V40_SETUP_FAIL,{}", e);
        std::process::exit(1);
    }

    println!("V40_CONFIG,ITERATIONS,{}", iterations);
    println!("V40_WORKSPACE,ML-KEM,{}", mlkem_ws);
    println!("V40_WORKSPACE,ML-DSA,{}", mldsa_ws);
    println!("V40_WORKSPACE,COMBINED,{}", combined_ws);

    let (p1, f1, n1) = mlkem_valid_flow(iterations);
    let (p2, f2, n2) = mldsa_valid_and_negative(iterations);
    let (p3, f3, n3) = combined_mlkem_mldsa_sequence(iterations);

    print_case("rust_mlkem_valid_flow", iterations, p1, f1, &n1);
    print_case("rust_mldsa_valid_and_negative", iterations, p2, f2, &n2);
    print_case("rust_combined_mlkem_mldsa_sequence", iterations, p3, f3, &n3);

    let pass_rows = [f1, f2, f3].iter().filter(|&&f| f == 0).count();
    let fail_rows = 3 - pass_rows;

    println!(
        "V40_SUMMARY,{},{},{},{}",
        3,
        pass_rows,
        fail_rows,
        if fail_rows == 0 { "PASS" } else { "FAIL" }
    );

    unsafe {
        OQS_destroy();
    }

    if fail_rows == 0 {
        std::process::exit(0);
    }

    std::process::exit(1);
}
