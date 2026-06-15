#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

TARGETS = {
    "x86_64": ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/sign.c",
    "ref": ROOT / "src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/sign.c",
}

FUNCTION_NAME = "mld_attempt_signature_generation"
OUTPUT_NAME = "attempt_generation"

# Approximate ML-DSA-44 sizes.
# This is a lifetime-analysis helper, not the final compiler stack truth.
TYPE_BYTES = {
    "mld_polymat": 16384,

    "mld_poly": 1024,
    "mld_polyvecl": 4096,
    "mld_polyveck": 4096,

    # Signature/key internal aliases often seen in sign.c.
    "mld_sig_z": 4096,
    "mld_sig_h": 4096,
    "mld_sig_c": 1024,
    "mld_pk_t1": 4096,

    # v19a attempt-generation local aliases.
    "mld_yvec": 4096,
    "w1tmp_u": 4096,
    "pointer": 8,

    "mld_sk_s1hat": 4096,
    "mld_sk_s2hat": 4096,
    "mld_sk_t0hat": 4096,

    # Small/basic types.
    "uint8_t": 1,
    "uint32_t": 4,
    "uint64_t": 8,
    "size_t": 8,
    "int": 4,
    "unsigned": 4,
    "unsigned int": 4,
}

CONST_VALUES = {
    "N": 256,
    "K": 4,
    "L": 4,
    "MLDSA_K": 4,
    "MLDSA_L": 4,

    "SEEDBYTES": 32,
    "CRHBYTES": 64,
    "TRBYTES": 64,
    "RNDBYTES": 32,
    "CTILDEBYTES": 32,
    "MLDSA_CTILDEBYTES": 32,

    "MLDSA_CRYPTO_PUBLICKEYBYTES": 1312,
    "MLDSA_CRYPTO_SECRETKEYBYTES": 2560,
    "MLDSA_CRYPTO_BYTES": 2420,
}


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


def find_function(text: str, function_name: str):
    """
    Find the real function definition, not a call site.

    Requires a C-like function definition line and skips prototypes.
    """
    pattern = re.compile(
        r"(?m)^\s*(?:static\s+)?[A-Za-z_][A-Za-z0-9_\s\*]+\b"
        + re.escape(function_name)
        + r"\s*\("
    )

    for m in pattern.finditer(text):
        header_start = text.rfind("\n", 0, m.start())
        header_start = 0 if header_start == -1 else header_start + 1

        brace_start = text.find("{", m.end())
        semi_start = text.find(";", m.end())

        if brace_start == -1:
            continue

        # Skip prototypes/declarations.
        if semi_start != -1 and semi_start < brace_start:
            continue

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
            continue

        start_line = text[:header_start].count("\n") + 1
        body = text[header_start:end]
        return start_line, body

    return None


def word_uses(body_lines, start_line: int, name: str):
    out = []
    word = re.compile(rf"\b{re.escape(name)}\b")

    for offset, line in enumerate(body_lines):
        if word.search(line):
            out.append(start_line + offset)

    return out


def parse_decl_vars(vars_part: str):
    out = []

    for part in vars_part.split(","):
        original = part.strip()
        p = original.split("=")[0].strip()

        is_pointer = "*" in p

        # Capture optional array expression.
        array_expr = "1"
        arr = re.search(r"\[([^\]]+)\]", p)
        if arr:
            array_expr = arr.group(1)

        p = re.sub(r"\[[^\]]+\]", "", p)
        p = p.replace("*", " ")
        tokens = p.split()

        if not tokens:
            continue

        name = tokens[-1]

        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            out.append((name, array_expr, is_pointer))

    return out


def scan_variant(variant: str, path: Path):
    text = path.read_text()

    found = find_function(text, FUNCTION_NAME)
    if not found:
        print(f"warning: {FUNCTION_NAME} not found in {variant}")
        return [], []

    start_line, body = found
    body_lines = body.splitlines()

    variables = {}
    unknown_types = set()

    # MLD_ALLOC(name, type, count, context)
    alloc_re = re.compile(
        r"\bMLD_ALLOC[A-Za-z0-9_]*\s*\(\s*"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
        r"(?P<type>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
        r"(?P<count>[^,\)]+)"
    )

    # MLD_FREE(name, type, count, context)
    free_re = re.compile(
        r"\bMLD_FREE[A-Za-z0-9_]*\s*\(\s*"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    )

    # Normal local declarations.
    decl_re = re.compile(
        r"^\s*(?:MLD_ALIGN\s+)?"
        r"(?P<type>mld_[A-Za-z0-9_]+|uint8_t|uint32_t|uint64_t|size_t|int|unsigned int|unsigned)\s+"
        r"(?P<vars>[^;]+);"
    )

    # Keep extracted source for manual inspection.
    source_md = RESULTS / f"v19a_{variant}_{OUTPUT_NAME}_source.md"
    with source_md.open("w") as f:
        f.write(f"# v19a extracted source: {variant} `{FUNCTION_NAME}`\n\n")
        f.write("```c\n")
        for offset, line in enumerate(body_lines):
            f.write(f"{start_line + offset:5d}: {line}\n")
        f.write("```\n")

    in_typedef_union = False

    for offset, line in enumerate(body_lines):
        abs_line = start_line + offset
        stripped = line.strip()

        # Ignore declarations inside local typedef union blocks.
        # Example:
        #   typedef union
        #   {
        #     mld_polyveck w1;
        #     mld_polyvecl tmp;
        #   } w1tmp_u;
        #
        # The real object is the allocated w1tmp_u object, not the union members.
        if stripped.startswith("typedef union"):
            in_typedef_union = True
            continue

        if in_typedef_union:
            typedef_name = re.search(r"}\s*([A-Za-z_][A-Za-z0-9_]*)\s*;", stripped)
            if typedef_name:
                name = typedef_name.group(1)
                if name not in TYPE_BYTES:
                    unknown_types.add(name)
                in_typedef_union = False
            continue

        m = alloc_re.search(stripped)
        if m:
            name = m.group("name")
            var_type = m.group("type")
            count = m.group("count")

            if var_type not in TYPE_BYTES:
                unknown_types.add(var_type)

            variables[name] = {
                "variant": variant,
                "function": OUTPUT_NAME,
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

            if var_type not in TYPE_BYTES:
                unknown_types.add(var_type)

            for name, array_expr, is_pointer in parse_decl_vars(vars_part):
                if name not in variables:
                    effective_type = "pointer" if is_pointer else var_type
                    variables[name] = {
                        "variant": variant,
                        "function": OUTPUT_NAME,
                        "name": name,
                        "type": effective_type if is_pointer else var_type,
                        "storage": "local_decl_pointer" if is_pointer else "local_decl",
                        "decl_line": abs_line,
                        "alloc_line": abs_line,
                        "free_line": "",
                        "approx_bytes": approx_bytes(effective_type, array_expr),
                        "raw_decl": stripped,
                    }

    rows = []

    for name, var in variables.items():
        uses = word_uses(body_lines, start_line, name)

        first_use = min(uses) if uses else var["decl_line"]
        last_use = max(uses) if uses else var["decl_line"]

        if var["free_line"] != "":
            last_use = int(var["free_line"])

        var["first_use"] = first_use
        var["last_use"] = last_use
        var["lifetime_lines"] = last_use - first_use + 1

        rows.append(var)

    csv_path = RESULTS / f"v19a_{variant}_{OUTPUT_NAME}_lifetime.csv"
    md_path = RESULTS / f"v19a_{variant}_{OUTPUT_NAME}_lifetime.md"

    rows_sorted = sorted(
        rows,
        key=lambda x: (-int(x["approx_bytes"]), int(x["first_use"]), x["name"]),
    )

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
        for row in rows_sorted:
            writer.writerow(row)

    with md_path.open("w") as f:
        f.write(f"# v19a lifetime map: {variant} `{FUNCTION_NAME}`\n\n")
        f.write("Approximate lexical lifetime map for the remaining ML-DSA signing hotspot.\n\n")
        f.write("| Name | Type | Storage | First | Last | Free | Approx bytes | Declaration |\n")
        f.write("|---|---|---|---:|---:|---:|---:|---|\n")

        for row in rows_sorted:
            free_line = row["free_line"] if row["free_line"] != "" else "-"
            f.write(
                f"| `{row['name']}` | `{row['type']}` | {row['storage']} | "
                f"{row['first_use']} | {row['last_use']} | {free_line} | "
                f"{row['approx_bytes']} | `{row['raw_decl']}` |\n"
            )

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    print(f"wrote {source_md}")

    return rows, sorted(unknown_types)


def write_reuse_candidates(all_rows):
    md_path = RESULTS / "v19a_attempt_reuse_candidates.md"

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
        f.write("# v19a possible attempt-generation reuse candidates\n\n")
        f.write("These are approximate candidates based on allocation/free and textual use.\n")
        f.write("This is not a proof of safety. Manually inspect before v19b.\n\n")
        f.write("| Variant | Function | Candidate A | Lifetime A | Candidate B | Lifetime B | Approx saving |\n")
        f.write("|---|---|---|---|---|---|---:|\n")

        for saved, a, b in candidates[:120]:
            f.write(
                f"| {a['variant']} | `{a['function']}` | "
                f"`{a['name']}: {a['type']}` | {a['first_use']}-{a['last_use']} | "
                f"`{b['name']}: {b['type']}` | {b['first_use']}-{b['last_use']} | "
                f"{saved} B |\n"
            )

    print(f"wrote {md_path}")


def write_unknown_types(unknown_by_variant):
    md_path = RESULTS / "v19a_unknown_types.md"

    with md_path.open("w") as f:
        f.write("# v19a unknown type-size entries\n\n")
        f.write("These types were detected but are not in the approximate size map.\n")
        f.write("If one of them is large, add it to TYPE_BYTES and rerun v19a.\n\n")
        f.write("| Variant | Unknown type |\n")
        f.write("|---|---|\n")

        for variant, types in unknown_by_variant.items():
            for typ in types:
                f.write(f"| {variant} | `{typ}` |\n")

    print(f"wrote {md_path}")


def write_summary(all_rows):
    md_path = RESULTS / "v19a_attempt_summary.md"

    large = [r for r in all_rows if int(r["approx_bytes"]) >= 1024]
    large.sort(key=lambda x: (-int(x["approx_bytes"]), x["variant"], int(x["first_use"])))

    with md_path.open("w") as f:
        f.write("# v19a attempt-generation summary\n\n")
        f.write("v19a analyzes the remaining signing hotspot after v17b/v18:\n\n")
        f.write("`mld_attempt_signature_generation`\n\n")
        f.write("## Largest detected objects\n\n")
        f.write("| Variant | Name | Type | First | Last | Approx bytes |\n")
        f.write("|---|---|---|---:|---:|---:|\n")

        for row in large[:40]:
            f.write(
                f"| {row['variant']} | `{row['name']}` | `{row['type']}` | "
                f"{row['first_use']} | {row['last_use']} | {row['approx_bytes']} |\n"
            )

        f.write("\n## Interpretation\n\n")
        f.write("This is an approximate lexical lifetime map. It helps decide whether v19b should use safe buffer reuse or caller-provided attempt workspace.\n")
        f.write("Do not treat this as a formal proof of safety.\n")

    print(f"wrote {md_path}")


def main() -> int:
    RESULTS.mkdir(exist_ok=True)

    all_rows = []
    unknown_by_variant = {}

    for variant, path in TARGETS.items():
        rows, unknown = scan_variant(variant, path)
        all_rows.extend(rows)
        unknown_by_variant[variant] = unknown

    write_reuse_candidates(all_rows)
    write_unknown_types(unknown_by_variant)
    write_summary(all_rows)

    print()
    print("v19a attempt-generation lifetime scan done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
