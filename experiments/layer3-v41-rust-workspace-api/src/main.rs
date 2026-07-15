mod crypto;
mod ffi;
mod workspace;

use crypto::CaseResult;
use workspace::PqcWorkspaceContext;

use std::env;

fn print_case(result: &CaseResult) {
    let status = if result.failed == 0 && result.passed == result.iterations {
        "PASS"
    } else {
        "FAIL"
    };

    println!(
        "V41_CASE,{},{},{},{},{},{}",
        result.name, result.iterations, result.passed, result.failed, status, result.notes
    );
}

fn main() {
    let iterations = env::var("V41_ITERATIONS")
        .ok()
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(100);

    crypto::initialize();

    let mut context = match PqcWorkspaceContext::new() {
        Ok(context) => context,
        Err(error) => {
            println!("V41_SETUP_FAIL,{}", error);
            crypto::shutdown();
            std::process::exit(1);
        }
    };

    println!("V41_CONFIG,ITERATIONS,{}", iterations);
    println!("V41_CONFIG,ALIGNMENT,{}", workspace::WORKSPACE_ALIGNMENT);

    println!("V41_WORKSPACE,ML-KEM,{}", context.mlkem_len());
    println!("V41_WORKSPACE,ML-DSA,{}", context.mldsa_len());
    println!("V41_WORKSPACE,COMBINED,{}", context.combined_len());

    let mut results: Vec<CaseResult> = Vec::new();

    results.push(CaseResult::from_bool(
        "workspace_size_accounting",
        context.sizes_match_expected(),
        "Workspace sizes match established lifecycle values",
    ));

    results.push(CaseResult::from_bool(
        "workspace_alignment",
        context.all_aligned(),
        "Both Rust-owned workspaces are 64-byte aligned",
    ));

    results.push(CaseResult::from_bool(
        "workspace_zero_initialization",
        context.all_zeroed(),
        "Both workspace allocations begin zero initialized",
    ));

    results.push(CaseResult::from_bool(
        "workspace_activation",
        context.activate().is_ok(),
        "C and x86_64 lifecycle setters accept Rust-owned buffers",
    ));

    let zeroization_ok = match PqcWorkspaceContext::new() {
        Ok(mut scratch) => {
            scratch.fill_for_validation(0xA5);

            let became_nonzero = !scratch.all_zeroed();

            scratch.zeroize_for_validation();

            became_nonzero && scratch.all_zeroed()
        }
        Err(_) => false,
    };

    results.push(CaseResult::from_bool(
        "workspace_zeroization_routine",
        zeroization_ok,
        "Live workspace wipe routine restores all bytes to zero",
    ));

    results.push(crypto::mlkem_flow(&mut context, iterations));
    results.push(crypto::mldsa_flow(&mut context, iterations));
    results.push(crypto::combined_flow(&mut context, iterations));

    for result in &results {
        print_case(result);
    }

    let total_rows = results.len();

    let pass_rows = results
        .iter()
        .filter(|result| result.failed == 0 && result.passed == result.iterations)
        .count();

    let fail_rows = total_rows - pass_rows;

    println!(
        "V41_SUMMARY,{},{},{},{}",
        total_rows,
        pass_rows,
        fail_rows,
        if fail_rows == 0 { "PASS" } else { "FAIL" }
    );

    crypto::shutdown();

    if fail_rows == 0 {
        std::process::exit(0);
    }

    std::process::exit(1);
}
