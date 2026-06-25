#!/usr/bin/env python3
from pathlib import Path
import re
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

FLAG = "MLK_CONFIG_EXPERIMENTAL_CALLER_KEYPAIR_WORKSPACE"
SOURCE_FN = "mlk_indcpa_keypair_derand"


def find_function_bounds(text: str, name: str):
    search_pos = 0

    while True:
        idx = text.find(name, search_pos)

        if idx == -1:
            raise RuntimeError(f"function definition not found: {name}")

        brace = text.find("{", idx)

        if brace == -1:
            raise RuntimeError(f"opening brace not found for {name}")

        between = text[idx:brace]

        if ";" in between or "(" not in between or ")" not in between:
            search_pos = idx + len(name)
            continue

        depth = 0

        for pos in range(brace, len(text)):
            ch = text[pos]

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1

                if depth == 0:
                    return idx, brace, pos + 1

        raise RuntimeError(f"closing brace not found for {name}")


def insert_v27_block(text: str, prefix: str):
    marker = f"{prefix}_v27_keypair_workspace_bytes"

    if marker in text:
        return text

    fn_start, _, _ = find_function_bounds(text, SOURCE_FN)
    line_start = text.rfind("\n", 0, fn_start) + 1

    block = f'''
#if defined({FLAG})

#define MLK_V27_WORKSPACE_ALIGN ((size_t)64)

#if defined(MLK_ALIGN)
#define MLK_V27_ALIGN_FIELD MLK_ALIGN
#elif defined(MLKEM_ALIGN)
#define MLK_V27_ALIGN_FIELD MLKEM_ALIGN
#else
#define MLK_V27_ALIGN_FIELD
#endif

typedef struct {{
    MLK_V27_ALIGN_FIELD mlk_polymat a;
    MLK_V27_ALIGN_FIELD mlk_polyvec e;
    MLK_V27_ALIGN_FIELD mlk_polyvec pkpv;
    MLK_V27_ALIGN_FIELD mlk_polyvec skpv;
    MLK_V27_ALIGN_FIELD mlk_polyvec_mulcache skpv_cache;
    uint8_t buf[2 * MLKEM_SYMBYTES];
    uint8_t coins_with_domain_separator[MLKEM_SYMBYTES + 1];
}} mlk_v27_keypair_workspace;

static _Thread_local mlk_v27_keypair_workspace *mlk_v27_tls_keypair_workspace;

size_t {prefix}_v27_keypair_workspace_bytes(void) {{
    return sizeof(mlk_v27_keypair_workspace);
}}

int {prefix}_v27_keypair_workspace_set(void *workspace, size_t workspace_bytes) {{
    if (workspace == 0 || workspace_bytes < sizeof(mlk_v27_keypair_workspace)) {{
        return -1;
    }}

    if (((size_t)workspace & (MLK_V27_WORKSPACE_ALIGN - 1u)) != 0u) {{
        return -2;
    }}

    mlk_v27_tls_keypair_workspace = (mlk_v27_keypair_workspace *)workspace;
    return 0;
}}

#define MLK_V27_REQUIRE_KEYPAIR_WORKSPACE()          \\
    do {{                                           \\
        if (mlk_v27_tls_keypair_workspace == 0) {{  \\
            return -1;                              \\
        }}                                          \\
    }} while (0)

#define MLK_V27_CLEAN_KEYPAIR_WORKSPACE() do {{ }} while (0)

#endif /* {FLAG} */

'''

    return text[:line_start] + block + text[line_start:]


def patch_keypair_function(text: str):
    _, body_start, fn_end = find_function_bounds(text, SOURCE_FN)

    before = text[:body_start + 1]
    body = text[body_start + 1:fn_end - 1]
    after = text[fn_end - 1:]

    if "MLK_V27_REQUIRE_KEYPAIR_WORKSPACE" in body:
        return text

    alloc_macro = r"(?:MLKEM_ALLOC|MLK_ALLOC|KYBER_ALLOC)"

    alloc_pat = re.compile(
        rf"(?P<indent>[ \t]*){alloc_macro}\s*\(\s*buf\s*,.*?"
        rf"{alloc_macro}\s*\(\s*skpv_cache\s*,.*?;\s*\n",
        re.S,
    )

    alloc_match = alloc_pat.search(body)

    if not alloc_match:
        raise RuntimeError(f"allocation block not found in {SOURCE_FN}")

    indent = alloc_match.group("indent")
    original_alloc_block = alloc_match.group(0)

    replacement_alloc_block = f'''{indent}#if defined({FLAG})
{indent}MLK_V27_REQUIRE_KEYPAIR_WORKSPACE();

{indent}uint8_t *buf = mlk_v27_tls_keypair_workspace->buf;
{indent}uint8_t *coins_with_domain_separator = mlk_v27_tls_keypair_workspace->coins_with_domain_separator;
{indent}mlk_polymat *a = &mlk_v27_tls_keypair_workspace->a;
{indent}mlk_polyvec *e = &mlk_v27_tls_keypair_workspace->e;
{indent}mlk_polyvec *pkpv = &mlk_v27_tls_keypair_workspace->pkpv;
{indent}mlk_polyvec *skpv = &mlk_v27_tls_keypair_workspace->skpv;
{indent}mlk_polyvec_mulcache *skpv_cache = &mlk_v27_tls_keypair_workspace->skpv_cache;
{indent}#else
{original_alloc_block}{indent}#endif
'''

    body = body[:alloc_match.start()] + replacement_alloc_block + body[alloc_match.end():]

    free_macro = r"(?:MLKEM_FREE|MLK_FREE|KYBER_FREE)"
    names = [
        "buf",
        "coins_with_domain_separator",
        "a",
        "e",
        "pkpv",
        "skpv",
        "skpv_cache",
    ]

    free_re = re.compile(
        rf"^[ \t]*{free_macro}\s*\(\s*(?P<name>"
        + "|".join(names)
        + r")\s*(?:,[^)]*)?\)\s*;\s*$",
        re.M,
    )

    matches = list(free_re.finditer(body))

    if not matches:
        raise RuntimeError(f"free block not found in {SOURCE_FN}")

    found = {m.group("name") for m in matches}
    missing = sorted(set(names) - found)

    if missing:
        raise RuntimeError(f"missing free lines in {SOURCE_FN}: {missing}")

    start = matches[0].start()
    end = matches[-1].end()

    original_free_block = body[start:end]
    free_indent_match = re.match(r"^[ \t]*", original_free_block)
    free_indent = free_indent_match.group(0) if free_indent_match else indent

    replacement_free_block = f'''{free_indent}#if defined({FLAG})
{free_indent}MLK_V27_CLEAN_KEYPAIR_WORKSPACE();
{free_indent}#else
{original_free_block}
{free_indent}#endif'''

    body = body[:start] + replacement_free_block + body[end:]

    return before + body + after


def patch_file(label: str, path: Path, prefix: str):
    text = path.read_text()

    backup = path.with_suffix(path.suffix + ".before_v27")

    if not backup.exists():
        shutil.copy2(path, backup)
        print(f"created backup: {backup}")
    else:
        print(f"backup already exists: {backup}")

    text = insert_v27_block(text, prefix)
    text = patch_keypair_function(text)

    path.write_text(text)
    print(f"patched {label}: {path}")


def main():
    for label, path, prefix in TARGETS:
        patch_file(label, path, prefix)


if __name__ == "__main__":
    main()
