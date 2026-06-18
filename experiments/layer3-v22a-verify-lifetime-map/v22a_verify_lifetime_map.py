#!/usr/bin/env python3
from pathlib import Path
import re
import csv

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"

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

# Approximate ML-DSA-44 constants.
CONSTANTS = {
    "MLDSA_K": 4,
    "MLDSA_L": 4,
    "MLDSA_N": 256,
    "MLDSA_SEEDBYTES": 32,
    "MLDSA_CRHBYTES": 64,
    "MLDSA_TRBYTES": 64,
    "MLDSA_CTILDEBYTES": 32,
    "MLDSA_OMEGA": 80,

    # ML-DSA-44 packing constants.
    # These are approximate/standard values used for attribution.
    "MLDSA_POLYW1_PACKEDBYTES": 192,
    "MLDSA_POLYZ_PACKEDBYTES": 576,
    "MLDSA_POLYT1_PACKEDBYTES": 320,
}

TYPE_SIZES = {
    "mld_poly": 1024,
    "mld_polyvecl": 4096,
    "mld_polyveck": 4096,
    "mld_yvec": 4096,
    "mld_polymat": 16384,

    # Common aliases/wrappers used in sign.c.
    "mld_pk_t1": 4096,
    "mld_sk_s1hat": 4096,
    "mld_sk_s2hat": 4096,
    "mld_sk_t0hat": 4096,
    "mld_signature_z": 4096,
    "mld_signature_h": 4096,
    "mld_zvec": 4096,
    "mld_hvec": 4096,
}


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def find_function(lines, function_name):
    pattern = re.compile(r"\b" + re.escape(function_name) + r"\b")

    for i, line in enumerate(lines):
        if not pattern.search(line):
            continue

        open_brace = None
        for j in range(i, min(i + 80, len(lines))):
            if ";" in lines[j] and "{" not in lines[j]:
                break
            if "{" in lines[j]:
                open_brace = j
                break

        if open_brace is None:
            continue

        depth = 0
        end = None
        for k in range(open_brace, len(lines)):
            for ch in lines[k]:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = k
                        break
            if end is not None:
                return i, end

    raise RuntimeError(f"cannot find function {function_name}")


def join_statements(lines, base_line):
    stmts = []
    current = []
    start_line = None

    for idx, line in enumerate(lines):
        line_no = base_line + idx
        stripped = line.strip()

        if not stripped:
            continue

        if start_line is None:
            start_line = line_no

        current.append(stripped)

        if ";" in stripped:
            stmts.append((start_line, " ".join(current)))
            current = []
            start_line = None

    return stmts


def eval_expr(expr):
    expr = expr.strip()
    expr = expr.replace("(", " ").replace(")", " ")
    parts = re.split(r"(\*|\+|-)", expr)

    # Only handle simple products/sums safely.
    if not parts:
        return None

    total = None
    op = None

    for raw in parts:
        token = raw.strip()
        if not token:
            continue

        if token in ("*", "+", "-"):
            op = token
            continue

        if token.isdigit():
            value = int(token)
        elif token in CONSTANTS:
            value = CONSTANTS[token]
        else:
            return None

        if total is None:
            total = value
        elif op == "*":
            total *= value
        elif op == "+":
            total += value
        elif op == "-":
            total -= value
        else:
            return None

    return total


def elem_size(typ):
    typ = typ.strip().replace("const ", "").replace("MLD_ALIGN ", "")

    if typ in TYPE_SIZES:
        return TYPE_SIZES[typ]
    if typ in ("uint8_t", "char", "unsigned char"):
        return 1
    if typ in ("uint16_t",):
        return 2
    if typ in ("uint32_t", "int32_t", "int", "unsigned"):
        return 4
    if typ in ("uint64_t", "size_t"):
        return 8

    return None


def estimate_size(typ, array_expr=None):
    base = elem_size(typ)
    if base is None:
        return None

    if array_expr is None:
        return base

    count = eval_expr(array_expr)
    if count is None:
        return None

    return base * count


def first_last_usage(lines, name, base_line):
    pat = re.compile(r"\b" + re.escape(name) + r"\b")
    hits = []

    for idx, line in enumerate(lines):
        if pat.search(line):
            hits.append(base_line + idx)

    if not hits:
        return "", ""

    return min(hits), max(hits)


def parse_statement(stmt):
    # Remove common qualifiers/macros.
    s = stmt.strip()
    s = s.replace("MLD_ALIGN ", "")
    s = re.sub(r"\bstatic\b", "", s).strip()

    # MLD_ALLOC(name, type, count, context)
    m = re.search(
        r"MLD_ALLOC\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([^,]+)\s*,",
        s,
    )
    if m:
        name, typ, arr = m.group(1), m.group(2), m.group(3)
        return typ, name, arr, "MLD_ALLOC"

    # MLD_V17B_ALLOC_MAT(mat)
    # In v21 this is caller-workspace backed, so count only as a pointer-like local.
    m = re.search(
        r"MLD_V17B_ALLOC_MAT\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)",
        s,
    )
    if m:
        return "mld_polymat *", m.group(1), None, "workspace_pointer"

    # type name[COUNT];
    m = re.match(
        r"(?:const\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]+)\s*\]",
        s,
    )
    if m:
        return m.group(1), m.group(2), m.group(3), "array"

    # type *name;
    m = re.match(
        r"(?:const\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)",
        s,
    )
    if m:
        return m.group(1) + " *", m.group(2), None, "pointer"

    # mld_type name;
    m = re.match(
        r"(?:const\s+)?(mld_[A-Za-z0-9_]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|;|,)",
        s,
    )
    if m:
        return m.group(1), m.group(2), None, "object"

    return None


def collect_locals(function_lines, base_line):
    rows = []
    statements = join_statements(function_lines, base_line)

    for line_no, stmt in statements:
        parsed = parse_statement(stmt)
        if parsed is None:
            continue

        typ, name, arr, kind = parsed

        if kind == "pointer" or kind == "workspace_pointer":
            size = 8
        else:
            size = estimate_size(typ, arr)

        first, last = first_last_usage(function_lines, name, base_line)

        rows.append({
            "line": line_no,
            "name": name,
            "type": typ if arr is None else f"{typ}[{arr}]",
            "kind": kind,
            "bytes": size,
            "first_use": first,
            "last_use": last,
            "source": stmt,
        })

    # Keep unique rows.
    seen = set()
    unique = []
    for row in rows:
        key = (row["line"], row["name"], row["type"], row["kind"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    return unique


def overlap(a, b):
    if not a["first_use"] or not a["last_use"]:
        return False
    if not b["first_use"] or not b["last_use"]:
        return False

    return not (a["last_use"] < b["first_use"] or b["last_use"] < a["first_use"])


def write_reports(variant, path):
    raw = path.read_text()
    clean = strip_comments(raw)
    lines = clean.splitlines(keepends=True)

    start, end = find_function(lines, "mld_sign_verify_internal")
    function_lines = lines[start:end + 1]
    base_line = start + 1

    locals_found = collect_locals(function_lines, base_line)

    RESULTS.mkdir(exist_ok=True)

    csv_path = RESULTS / f"v22a_verify_lifetime_map_{variant}.csv"
    md_path = RESULTS / f"v22a_verify_lifetime_map_{variant}.md"

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "variant", "line", "name", "type", "kind", "bytes",
                "first_use", "last_use", "source"
            ],
        )
        writer.writeheader()
        for item in locals_found:
            row = dict(item)
            row["variant"] = variant
            writer.writerow(row)

    large = sorted(
        locals_found,
        key=lambda x: x["bytes"] if x["bytes"] is not None else -1,
        reverse=True,
    )

    known_non_pointer_total = sum(
        item["bytes"] or 0
        for item in locals_found
        if item["kind"] != "pointer"
    )

    unknown = [item for item in locals_found if item["bytes"] is None]

    candidates = []
    big_buffers = [
        x for x in large
        if x["bytes"] is not None and x["bytes"] >= 512 and x["first_use"] and x["last_use"]
    ]

    for i in range(len(big_buffers)):
        for j in range(i + 1, len(big_buffers)):
            a = big_buffers[i]
            b = big_buffers[j]
            if not overlap(a, b):
                candidates.append((a, b))

    with md_path.open("w") as f:
        f.write(f"# v22a mld_sign_verify_internal lifetime map: {variant}\n\n")
        f.write(f"Source: `{path}`\n\n")
        f.write(f"Function range: lines {start + 1}-{end + 1}\n\n")

        f.write("## Large/local buffers\n\n")
        f.write("| Name | Type | Kind | Approx bytes | First use | Last use | Decl line |\n")
        f.write("|---|---|---|---:|---:|---:|---:|\n")

        for item in large:
            f.write(
                f"| `{item['name']}` | `{item['type']}` | {item['kind']} | "
                f"{item['bytes'] if item['bytes'] is not None else ''} | "
                f"{item['first_use']} | {item['last_use']} | {item['line']} |\n"
            )

        f.write("\n")
        f.write(f"Known non-pointer local total: **{known_non_pointer_total} B**\n\n")

        if unknown:
            f.write("## Unknown-size locals\n\n")
            f.write("| Name | Type | Kind | Decl line | Source |\n")
            f.write("|---|---|---|---:|---|\n")
            for item in unknown:
                f.write(
                    f"| `{item['name']}` | `{item['type']}` | {item['kind']} | "
                    f"{item['line']} | `{item['source']}` |\n"
                )
            f.write("\n")
        else:
            f.write("Unknown-size locals: none\n\n")

        f.write("## Simple non-overlap candidates\n\n")
        if not candidates:
            f.write("No obvious non-overlap candidates found by this simple scanner.\n\n")
        else:
            f.write("| A | A lifetime | B | B lifetime |\n")
            f.write("|---|---|---|---|\n")
            for a, b in candidates:
                f.write(
                    f"| `{a['name']}` | {a['first_use']}-{a['last_use']} | "
                    f"`{b['name']}` | {b['first_use']}-{b['last_use']} |\n"
                )
            f.write("\n")

        f.write("## Interpretation reminder\n\n")
        f.write(
            "This is a source-level attribution map. "
            "The compiler `.su` stack report remains the source for actual frame size. "
            "Use this output to decide what v22b should move into caller-provided verify workspace.\n"
        )

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")


def main():
    for variant, path in TARGETS:
        write_reports(variant, path)


if __name__ == "__main__":
    main()
