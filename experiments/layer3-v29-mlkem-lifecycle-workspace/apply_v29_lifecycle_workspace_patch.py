#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path.home() / "pqc/liboqs"

TARGETS = [
    (
        "x86_64",
        ROOT / "src/kem/ml_kem/mlkem-native_ml-kem-768_x86_64/mlkem/src/indcpa.c",
        "PQCP_MLKEM_NATIVE_MLKEM768_X86_64",
    ),
    (
        "ref",
        ROOT / "src/kem/ml_kem/mlkem-native_ml-kem-768_ref/mlkem/src/indcpa.c",
        "PQCP_MLKEM_NATIVE_MLKEM768_C",
    ),
]

V29_FLAG = "MLK_CONFIG_EXPERIMENTAL_COMPACT_LIFECYCLE_WORKSPACE"
V26_FLAG = "MLK_CONFIG_EXPERIMENTAL_CALLER_ENC_WORKSPACE"
V27_FLAG = "MLK_CONFIG_EXPERIMENTAL_CALLER_KEYPAIR_WORKSPACE"
V28_FLAG = "MLK_CONFIG_EXPERIMENTAL_CALLER_DEC_WORKSPACE"

INSERT_AFTER = "#endif /* MLK_CONFIG_EXPERIMENTAL_CALLER_DEC_WORKSPACE */"


def make_block(prefix: str) -> str:
    return f'''

#if defined({V29_FLAG}) && defined({V26_FLAG}) && defined({V27_FLAG}) && defined({V28_FLAG})

#define MLK_V29_WORKSPACE_ALIGN ((size_t)64)

typedef struct {{
    union {{
        mlk_v26_enc_workspace enc;
        mlk_v27_keypair_workspace keypair;
        mlk_v28_dec_workspace dec;
    }} op;
}} mlk_v29_lifecycle_workspace;

size_t {prefix}_v29_lifecycle_workspace_bytes(void) {{
    return sizeof(mlk_v29_lifecycle_workspace);
}}

int {prefix}_v29_lifecycle_workspace_set(void *workspace, size_t workspace_bytes) {{
    mlk_v29_lifecycle_workspace *ws = 0;

    if (workspace == 0 || workspace_bytes < sizeof(mlk_v29_lifecycle_workspace)) {{
        return -1;
    }}

    if (((size_t)workspace & (MLK_V29_WORKSPACE_ALIGN - 1u)) != 0u) {{
        return -2;
    }}

    ws = (mlk_v29_lifecycle_workspace *)workspace;

    mlk_v26_tls_enc_workspace = &ws->op.enc;
    mlk_v27_tls_keypair_workspace = &ws->op.keypair;
    mlk_v28_tls_dec_workspace = &ws->op.dec;

    return 0;
}}

#endif /* {V29_FLAG} */

'''


def patch_file(label: str, path: Path, prefix: str):
    text = path.read_text()

    marker = f"{prefix}_v29_lifecycle_workspace_bytes"

    if marker in text:
        print(f"already patched {label}: {path}")
        return

    backup = path.with_suffix(path.suffix + ".before_v29")

    if not backup.exists():
        shutil.copy2(path, backup)
        print(f"created backup: {backup}")
    else:
        print(f"backup already exists: {backup}")

    idx = text.find(INSERT_AFTER)

    if idx == -1:
        raise RuntimeError(f"could not find v28 insertion point in {path}")

    end = idx + len(INSERT_AFTER)
    text = text[:end] + make_block(prefix) + text[end:]

    path.write_text(text)
    print(f"patched {label}: {path}")


def main():
    for label, path, prefix in TARGETS:
        patch_file(label, path, prefix)


if __name__ == "__main__":
    main()
