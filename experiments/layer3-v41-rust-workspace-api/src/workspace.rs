use crate::ffi::{
    PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes,
    PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_set,
    PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes,
    PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_set,
    PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes,
    PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_set,
    PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes,
    PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_set,
};

use std::alloc::{alloc_zeroed, dealloc, Layout};
use std::fmt;
use std::ptr::NonNull;
use std::sync::atomic::{compiler_fence, Ordering};

pub const WORKSPACE_ALIGNMENT: usize = 64;

pub const EXPECTED_MLKEM_WORKSPACE_BYTES: usize = 13_088;
pub const EXPECTED_MLDSA_WORKSPACE_BYTES: usize = 44_064;
pub const EXPECTED_COMBINED_WORKSPACE_BYTES: usize =
    EXPECTED_MLKEM_WORKSPACE_BYTES + EXPECTED_MLDSA_WORKSPACE_BYTES;

#[derive(Debug)]
pub struct WorkspaceError {
    message: String,
}

impl WorkspaceError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl fmt::Display for WorkspaceError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for WorkspaceError {}

struct AlignedWorkspace {
    ptr: NonNull<u8>,
    len: usize,
    layout: Layout,
}

impl AlignedWorkspace {
    fn new(len: usize) -> Result<Self, WorkspaceError> {
        if len == 0 {
            return Err(WorkspaceError::new(
                "workspace byte-size function returned zero",
            ));
        }

        let layout = Layout::from_size_align(len, WORKSPACE_ALIGNMENT)
            .map_err(|e| WorkspaceError::new(format!("invalid workspace layout: {e}")))?;

        let raw = unsafe { alloc_zeroed(layout) };

        let ptr = NonNull::new(raw)
            .ok_or_else(|| WorkspaceError::new(format!("failed to allocate {len} bytes")))?;

        Ok(Self { ptr, len, layout })
    }

    fn as_mut_ptr(&mut self) -> *mut u8 {
        self.ptr.as_ptr()
    }

    fn len(&self) -> usize {
        self.len
    }

    fn address(&self) -> usize {
        self.ptr.as_ptr() as usize
    }

    fn is_aligned(&self) -> bool {
        self.address() % WORKSPACE_ALIGNMENT == 0
    }

    fn is_zeroed(&self) -> bool {
        let bytes = unsafe { std::slice::from_raw_parts(self.ptr.as_ptr(), self.len) };
        bytes.iter().all(|&byte| byte == 0)
    }

    fn fill_for_validation(&mut self, value: u8) {
        unsafe {
            std::ptr::write_bytes(self.ptr.as_ptr(), value, self.len);
        }
    }

    fn wipe(&mut self) {
        for offset in 0..self.len {
            unsafe {
                std::ptr::write_volatile(self.ptr.as_ptr().add(offset), 0);
            }
        }

        compiler_fence(Ordering::SeqCst);
    }
}

impl Drop for AlignedWorkspace {
    fn drop(&mut self) {
        self.wipe();

        unsafe {
            dealloc(self.ptr.as_ptr(), self.layout);
        }
    }
}

pub struct PqcWorkspaceContext {
    mlkem: AlignedWorkspace,
    mldsa: AlignedWorkspace,
}

impl PqcWorkspaceContext {
    pub fn new() -> Result<Self, WorkspaceError> {
        let mlkem_len = mlkem_workspace_bytes();
        let mldsa_len = mldsa_workspace_bytes();

        Ok(Self {
            mlkem: AlignedWorkspace::new(mlkem_len)?,
            mldsa: AlignedWorkspace::new(mldsa_len)?,
        })
    }

    pub fn mlkem_len(&self) -> usize {
        self.mlkem.len()
    }

    pub fn mldsa_len(&self) -> usize {
        self.mldsa.len()
    }

    pub fn combined_len(&self) -> usize {
        self.mlkem_len() + self.mldsa_len()
    }

    pub fn sizes_match_expected(&self) -> bool {
        self.mlkem_len() == EXPECTED_MLKEM_WORKSPACE_BYTES
            && self.mldsa_len() == EXPECTED_MLDSA_WORKSPACE_BYTES
            && self.combined_len() == EXPECTED_COMBINED_WORKSPACE_BYTES
    }

    pub fn all_aligned(&self) -> bool {
        self.mlkem.is_aligned() && self.mldsa.is_aligned()
    }

    pub fn all_zeroed(&self) -> bool {
        self.mlkem.is_zeroed() && self.mldsa.is_zeroed()
    }

    pub fn activate(&mut self) -> Result<(), WorkspaceError> {
        let mlkem_c_len = unsafe { PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes() };
        let mlkem_x86_len =
            unsafe { PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes() };

        let mldsa_c_len = unsafe { PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes() };
        let mldsa_x86_len =
            unsafe { PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes() };

        let mlkem_c_ok = mlkem_c_len > 0
            && unsafe {
                PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_set(
                    self.mlkem.as_mut_ptr(),
                    mlkem_c_len,
                )
            } == 0;

        let mlkem_x86_ok = mlkem_x86_len > 0
            && unsafe {
                PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_set(
                    self.mlkem.as_mut_ptr(),
                    mlkem_x86_len,
                )
            } == 0;

        let mldsa_c_ok = mldsa_c_len > 0
            && unsafe {
                PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_set(
                    self.mldsa.as_mut_ptr(),
                    mldsa_c_len,
                )
            } == 0;

        let mldsa_x86_ok = mldsa_x86_len > 0
            && unsafe {
                PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_set(
                    self.mldsa.as_mut_ptr(),
                    mldsa_x86_len,
                )
            } == 0;

        if !mlkem_c_ok {
            return Err(WorkspaceError::new(
                "ML-KEM C lifecycle workspace activation failed",
            ));
        }

        if !mlkem_x86_ok {
            return Err(WorkspaceError::new(
                "ML-KEM x86_64 lifecycle workspace activation failed",
            ));
        }

        if !mldsa_c_ok {
            return Err(WorkspaceError::new(
                "ML-DSA C lifecycle workspace activation failed",
            ));
        }

        if !mldsa_x86_ok {
            return Err(WorkspaceError::new(
                "ML-DSA x86_64 lifecycle workspace activation failed",
            ));
        }

        Ok(())
    }

    pub fn with_active<R>(&mut self, operation: impl FnOnce() -> R) -> Result<R, WorkspaceError> {
        self.activate()?;
        Ok(operation())
    }

    pub(crate) fn fill_for_validation(&mut self, value: u8) {
        self.mlkem.fill_for_validation(value);
        self.mldsa.fill_for_validation(value);
    }

    pub(crate) fn zeroize_for_validation(&mut self) {
        self.mlkem.wipe();
        self.mldsa.wipe();
    }
}

fn mlkem_workspace_bytes() -> usize {
    unsafe {
        let c = PQCP_MLKEM_NATIVE_MLKEM768_C_v29_lifecycle_workspace_bytes();
        let x86 = PQCP_MLKEM_NATIVE_MLKEM768_X86_64_v29_lifecycle_workspace_bytes();
        c.max(x86)
    }
}

fn mldsa_workspace_bytes() -> usize {
    unsafe {
        let c = PQCP_MLDSA_NATIVE_MLDSA44_C_v24_lifecycle_workspace_bytes();
        let x86 = PQCP_MLDSA_NATIVE_MLDSA44_X86_64_v24_lifecycle_workspace_bytes();
        c.max(x86)
    }
}
