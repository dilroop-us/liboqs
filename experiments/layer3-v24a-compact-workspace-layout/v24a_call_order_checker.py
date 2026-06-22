#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT = RESULTS / "v24a_call_order_checks.md"

TARGETS = [
    (
        "x86_64",
        ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c",
    ),
    (
        "ref",
        ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c",
    ),
]


def extract_function(text, name):
    start = text.find(name)
    if start == -1:
        return None

    brace = text.find("{", start)
    if brace == -1:
        return None

    depth = 0

    for i in range(brace, len(text)):
        ch = text[i]

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1

            if depth == 0:
                return text[start:i + 1]

    return None


def line_no(text, index):
    if index < 0:
        return 0

    return text[:index].count("\n") + 1


report = "# Layer 3 v24a call-order and overlap checks\n\n"
overall_pass = True

for variant, path in TARGETS:
    text = path.read_text()

    keypair = extract_function(text, "int mld_sign_keypair_internal")
    pk_from_sk = extract_function(text, "int mld_sign_pk_from_sk")

    report += f"## {variant}\n\n"
    report += f"Source: `{path}`\n\n"

    if keypair is None:
        report += "- FAIL: could not extract `mld_sign_keypair_internal`\n\n"
        overall_pass = False
    else:
        cleanup_idx = keypair.find("cleanup:")
        clean_idx = keypair.find("MLD_V23B_CLEAN_KEYGEN_WORKSPACE")
        pct_idx = keypair.find("return mld_check_pct")

        cleanup_line = line_no(keypair, cleanup_idx)
        clean_line = line_no(keypair, clean_idx)
        pct_line = line_no(keypair, pct_idx)

        ok_clean_before_pct = clean_idx != -1 and pct_idx != -1 and clean_idx < pct_idx

        report += "### keypair_internal\n\n"
        report += f"- cleanup label line inside extracted function: {cleanup_line}\n"
        report += f"- `MLD_V23B_CLEAN_KEYGEN_WORKSPACE` line inside extracted function: {clean_line}\n"
        report += f"- `return mld_check_pct` line inside extracted function: {pct_line}\n"
        report += f"- keygen workspace cleaned before PCT/sign-verify transition: {'PASS' if ok_clean_before_pct else 'FAIL'}\n\n"

        if not ok_clean_before_pct:
            overall_pass = False

    if pk_from_sk is None:
        report += "- FAIL: could not extract `mld_sign_pk_from_sk`\n\n"
        overall_pass = False
    else:
        clean_idx = pk_from_sk.find("MLD_V23B_CLEAN_KEYGEN_WORKSPACE")

        sign_like_calls = []

        for needle in [
            "mld_sign_signature",
            "mld_sign_verify",
            "mld_check_pct",
            "signature_internal",
            "verify_internal",
        ]:
            if needle in pk_from_sk:
                sign_like_calls.append(needle)

        report += "### pk_from_sk\n\n"
        report += f"- `MLD_V23B_CLEAN_KEYGEN_WORKSPACE` present: {'PASS' if clean_idx != -1 else 'FAIL'}\n"
        report += f"- nested sign/verify-like calls found: {', '.join(sign_like_calls) if sign_like_calls else 'none'}\n\n"

        if clean_idx == -1:
            overall_pass = False

report += "## Overall result\n\n"

if overall_pass:
    report += (
        "PASS: v24a call-order analysis supports compact workspace modeling. "
        "Keygen/provisioning buffers can be treated as operation-specific temporary memory, "
        "provided v24b uses one workspace per thread/context and does not allow concurrent "
        "operations on the same workspace.\n"
    )
else:
    report += (
        "FAIL: one or more call-order checks failed. Review source before implementing v24b.\n"
    )

OUT.write_text(report)

print(f"wrote {OUT}")
print("overall_pass=" + str(overall_pass))
