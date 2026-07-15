use std::env;
use std::path::PathBuf;

fn main() {
    let liboqs_build = env::var("LIBOQS_V41_BUILD")
        .expect("LIBOQS_V41_BUILD must point to the optimized liboqs build directory");

    let lib_dir = PathBuf::from(&liboqs_build).join("lib");

    println!("cargo:rustc-link-search=native={}", lib_dir.display());
    println!("cargo:rustc-link-lib=static=oqs");

    println!("cargo:rustc-link-lib=dylib=m");
    println!("cargo:rustc-link-lib=dylib=dl");
    println!("cargo:rustc-link-lib=dylib=pthread");

    println!("cargo:rerun-if-env-changed=LIBOQS_V41_BUILD");
}
