#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path.home() / "pqc/liboqs"

TARGETS = {
    "x86_64": ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c",
    "ref": ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c",
}

FUNCTIONS = [
    ("signature_internal", "mld_sign_signature_internal"),
    ("verify_internal", "mld_sign_verify_internal"),
    ("mld_compute_pack_t0_t1", "mld_compute_pack_t0_t1"),
]

# Approximate ML-DSA-44 sizes.
# Exact compiler stack is still measured by -fstack-usage;
# this script only helps identify candidate lifetime regions.
TYPE_BYTES = {
    "mld_polymat": 16384,
    "mld_polyvecl": 4096,
    "mld_polyveck": 4096,
    "mld_poly": 1024,

    # ML-DSA-44 internal secret-key/vector aliases.
    # Approximate sizes: 4 polynomials * 256 coeffs * 4 bytes.
    "mld_sk_s1hat": 4096,
    "mld_sk_s2hat": 4096,
    "mld_sk_t0hat": 4096,

    # Common signature/public-key aliases, approximate.
    "mld_sig_z": 4096,
    "mld_sig_h": 4096,
    "mld_sig_c": 1024,
    "mld_pk_t1": 4096,

    "uint8_t": 1,
    "uint32_t": 4,
    "uint64_t": 8,
    "size_t": 8,
    "int": 4,
}

CONST_VALUES = {
    "SEEDBYTES": 32,
    "CRHBYTES": 64,
    "TRBYTES": 64,
    "RNDBYTES": 32,
    "CTILDEBYTES": 32,
    "MLDSA_CRYPTO_PUBLICKEYBYTES": 1312,
    "MLDSA_CRYPTO_SECRETKEYBYTES": 2560,
    "MLDSA_CRYPTO_BYTES": 2420,
}


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def find_function(text: str, function_name: str):
    idx = text.find(function_name)
    if idx == -1:
        return None

    # Move back to the beginning of the line/header.
    start = text.rfind("\n", 0, idx)
    start = 0 if start == -1 else start + 1

    brace_start = text.find("{", idx)
    if brace_start == -1:
        return None

    depth = 0
    end = None

    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        return None

    start_line = text[:start].count("\n") + 1
    body = text[start:end]
    return start_line, body


def eval_count(expr: str) -> int:
    expr = expr.strip()

    for name, value in CONST_VALUES.items():
        expr = re.sub(rf"\b{name}\b", str(value), expr)

    expr = expr.replace(" ", "")

    if re.fullmatch(r"[0-9+\-*/()]+", expr):
        try:
            return int(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            return 1

    return 1


def approx_bytes(var_type: str, count_expr: str = "1") -> int:
    base = TYPE_BYTES.get(var_type, 0)
    count = eval_count(count_expr)
    return base * count


def word_uses(body_lines, start_line: int, name: str):
    out = []
    word = re.compile(rf"\b{re.escape(name)}\b")

    for offset, line in enumerate(body_lines):
        if word.search(line):
            out.append(start_line + offset)

    return out


def scan_function(variant: str, path: Path, output_name: str, function_name: str, out_dir: Path):
    text = path.read_text()
    clean = strip_comments(text)

    found = find_function(clean, function_name)
    if not found:
        print(f"warning: function not found: {variant} {function_name}")
        return []

    start_line, body = found
    body_lines = body.splitlines()

    variables = {}

    # Detect v16 caller workspace matrix.
    v16_alloc_re = re.compile(r"MLD_V16_ALLOC_MAT\s*\(\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\)")
    v16_free_re = re.compile(r"MLD_V16_FREE_MAT\s*\(\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\)")

    # Detect allocation macros:
    # MLD_ALLOC(name, type, count, context)
    alloc_re = re.compile(
        r"\bMLD_ALLOC[A-Za-z0-9_]*\s*\(\s*"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
        r"(?P<type>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
        r"(?P<count>[^,\)]+)"
    )

    free_re = re.compile(
        r"\bMLD_FREE[A-Za-z0-9_]*\s*\(\s*"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    )

    # Detect simple local declarations.
    decl_re = re.compile(
        r"^\s*(?:MLD_ALIGN\s+)?(?P<type>mld_[A-Za-z0-9_]+|uint8_t|uint32_t|uint64_t|size_t|int|unsigned int)\s+(?P<vars>[^;]+);"
    )

    for offset, line in enumerate(body_lines):
        abs_line = start_line + offset
        stripped = line.strip()

        m = v16_alloc_re.search(stripped)
        if m:
            name = m.group("name")
            variables[name] = {
                "variant": variant,
                "function": output_name,
                "name": name,
                "type": "mld_polymat",
                "storage": "caller_workspace",
                "decl_line": abs_line,
                "alloc_line": abs_line,
                "free_line": "",
                "approx_bytes": TYPE_BYTES["mld_polymat"],
                "raw_decl": stripped,
            }
            continue

        m = alloc_re.search(stripped)
        if m:
            name = m.group("name")
            var_type = m.group("type")
            count = m.group("count")
            variables[name] = {
                "variant": variant,
                "function": output_name,
                "name": name,
                "type": var_type,
                "storage": "MLD_ALLOC",
                "decl_line": abs_line,
                "alloc_line": abs_line,
                "free_line": "",
                "approx_bytes": approx_bytes(var_type, count),
                "raw_decl": stripped,
            }
            continue

        m = v16_free_re.search(stripped)
        if m:
            name = m.group("name")
            if name in variables:
                variables[name]["free_line"] = abs_line
            continue

        m = free_re.search(stripped)
        if m:
            name = m.group("name")
            if name in variables:
                variables[name]["free_line"] = abs_line
            continue

        m = decl_re.match(stripped)
        if m:
            var_type = m.group("type")
            vars_part = m.group("vars")

            # Split basic declarations like: uint8_t *rho, *tr, *key;
            for part in vars_part.split(","):
                p = part.strip().split("=")[0].strip()
                p = re.sub(r"\[[^\]]*\]", "", p)
                p = p.replace("*", " ")
                tokens = p.split()
                if not tokens:
                    continue

                name = tokens[-1]
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
                    continue

                if name not in variables:
                    variables[name] = {
                        "variant": variant,
                        "function": output_name,
                        "name": name,
                        "type": var_type,
                        "storage": "local_decl",
                        "decl_line": abs_line,
                        "alloc_line": abs_line,
                        "free_line": "",
                        "approx_bytes": approx_bytes(var_type, "1"),
                        "raw_decl": stripped,
                    }

    rows = []

    for name, var in variables.items():
        uses = word_uses(body_lines, start_line, name)

        first_use = min(uses) if uses else var["decl_line"]
        last_use = max(uses) if uses else var["decl_line"]

        # Prefer explicit free line as lifetime end when available.
        if var["free_line"] != "":
            last_use = int(var["free_line"])

        var["first_use"] = first_use
        var["last_use"] = last_use
        var["lifetime_lines"] = last_use - first_use + 1

        rows.append(var)

    csv_path = out_dir / f"v17a_{variant}_{output_name}_lifetime.csv"
    md_path = out_dir / f"v17a_{variant}_{output_name}_lifetime.md"

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant",
                "function",
                "name",
                "type",
                "storage",
                "decl_line",
                "alloc_line",
                "free_line",
                "first_use",
                "last_use",
                "lifetime_lines",
                "approx_bytes",
                "raw_decl",
            ],
        )
        writer.writeheader()
        for row in sorted(rows, key=lambda x: (-int(x["approx_bytes"]), int(x["first_use"]), x["name"])):
            writer.writerow(row)

    with md_path.open("w") as f:
        f.write(f"# v17a lifetime map: {variant} `{output_name}`\n\n")
        f.write("Approximate lexical lifetime map. MLD_ALLOC/MLD_FREE macros are detected when visible.\n\n")
        f.write("| Name | Type | Storage | First | Last | Free | Approx bytes | Declaration |\n")
        f.write("|---|---|---|---:|---:|---:|---:|---|\n")

        for row in sorted(rows, key=lambda x: (-int(x["approx_bytes"]), int(x["first_use"]), x["name"])):
            free_line = row["free_line"] if row["free_line"] != "" else "-"
            f.write(
                f"| `{row['name']}` | `{row['type']}` | {row['storage']} | "
                f"{row['first_use']} | {row['last_use']} | {free_line} | "
                f"{row['approx_bytes']} | `{row['raw_decl']}` |\n"
            )

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")

    return rows


def write_reuse_candidates(all_rows, out_dir: Path):
    md_path = out_dir / "v17a_reuse_candidates.md"

    large = [r for r in all_rows if int(r["approx_bytes"]) >= 1024]
    candidates = []

    for i, a in enumerate(large):
        for b in large[i + 1:]:
            if a["variant"] != b["variant"]:
                continue
            if a["function"] != b["function"]:
                continue
            if a["name"] == b["name"]:
                continue

            a_first, a_last = int(a["first_use"]), int(a["last_use"])
            b_first, b_last = int(b["first_use"]), int(b["last_use"])

            separated = a_last < b_first or b_last < a_first
            if not separated:
                continue

            saved = min(int(a["approx_bytes"]), int(b["approx_bytes"]))
            candidates.append((saved, a, b))

    candidates.sort(key=lambda x: (-x[0], x[1]["variant"], x[1]["function"]))

    with md_path.open("w") as f:
        f.write("# v17a possible buffer reuse candidates\n\n")
        f.write("Approximate candidates based on allocation/free and textual use.\n")
        f.write("This is not a proof of safety. Manually inspect each candidate before v17b.\n\n")
        f.write("| Variant | Function | Candidate A | Lifetime A | Candidate B | Lifetime B | Approx possible saving |\n")
        f.write("|---|---|---|---|---|---|---:|\n")

        for saved, a, b in candidates[:120]:
            f.write(
                f"| {a['variant']} | `{a['function']}` | "
                f"`{a['name']}: {a['type']}` | {a['first_use']}-{a['last_use']} | "
                f"`{b['name']}: {b['type']}` | {b['first_use']}-{b['last_use']} | "
                f"{saved} B |\n"
            )

    print(f"wrote {md_path}")


def main() -> int:
    out_dir = ROOT / "layer3-results"
    out_dir.mkdir(exist_ok=True)

    all_rows = []

    for variant, path in TARGETS.items():
        for output_name, function_name in FUNCTIONS:
            all_rows.extend(scan_function(variant, path, output_name, function_name, out_dir))

    write_reuse_candidates(all_rows, out_dir)

    print()
    print("v17a lifetime scan done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
