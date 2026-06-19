#!/usr/bin/env python3
from pathlib import Path
import csv
import re

ROOT = Path.home() / "pqc/liboqs"
BUILD = ROOT / "build-v23a-keygen-lifetime-map"
RESULTS = ROOT / "layer3-results"

TARGETS = ["keypair_internal", "pk_from_sk"]

CONSTANTS = {
    "MLDSA_K": 4,
    "MLDSA_L": 4,
    "MLDSA_N": 256,

    "MLDSA_SEEDBYTES": 32,
    "MLDSA_CRHBYTES": 64,
    "MLDSA_TRBYTES": 64,
    "MLDSA_CTILDEBYTES": 32,
    "MLDSA_RNDBYTES": 32,

    "MLDSA_CRYPTO_PUBLICKEYBYTES": 1312,
    "MLDSA_CRYPTO_SECRETKEYBYTES": 2560,
    "MLDSA_CRYPTO_BYTES": 2420,

    "MLDSA_POLYT1_PACKEDBYTES": 320,
    "MLDSA_POLYT0_PACKEDBYTES": 416,
    "MLDSA_POLYW1_PACKEDBYTES": 192,
    "MLDSA_POLYZ_PACKEDBYTES": 576,

    # Conservative helper constants for source attribution.
    "MLDSA_ETA": 2,
    "MLDSA_OMEGA": 80,
}

TYPE_SIZES = {
    "mld_poly": 1024,
    "mld_polyvecl": 4096,
    "mld_polyveck": 4096,
    "mld_yvec": 4096,
    "mld_polymat": 16384,

    # Common wrappers/aliases.
    "mld_pk_t1": 4096,
    "mld_sk_s1hat": 4096,
    "mld_sk_s2hat": 4096,
    "mld_sk_t0hat": 4096,

    "mld_sk_s1": 4096,
    "mld_sk_s2": 4096,
    "mld_sk_t0": 4096,
    "mld_signature_z": 4096,
    "mld_signature_h": 4096,
    "mld_zvec": 4096,
    "mld_hvec": 4096,
}

SU_RE = re.compile(r"^(.*?):(\d+):(\d+):([^\t]+)\t(\d+)\t(.+)$")


def variant_from_path(path: str) -> str:
    if "mldsa-native_ml-dsa-44_x86_64" in path:
        return "x86_64"
    if "mldsa-native_ml-dsa-44_ref" in path:
        return "ref"
    return "unknown"


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"//.*", "", text)
    return text


def load_target_stack_rows():
    rows = []

    for su in BUILD.rglob("*.su"):
        for line in su.read_text(errors="replace").splitlines():
            m = SU_RE.match(line)
            if not m:
                continue

            src, line_no, col_no, function, bytes_s, kind = m.groups()

            if "mldsa-native_ml-dsa-44" not in src:
                continue

            for target in TARGETS:
                if target in function:
                    rows.append({
                        "target": target,
                        "variant": variant_from_path(src),
                        "source_file": Path(src),
                        "line": int(line_no),
                        "column": int(col_no),
                        "function": function,
                        "stack_bytes": int(bytes_s),
                        "stack_kind": kind,
                    })

    rows.sort(key=lambda r: (r["target"], r["variant"]))
    return rows


def find_function_by_start_line(lines, start_line):
    start_idx = start_line - 1

    open_brace = None
    for i in range(start_idx, min(start_idx + 120, len(lines))):
        if "{" in lines[i]:
            open_brace = i
            break

        if ";" in lines[i]:
            break

    if open_brace is None:
        raise RuntimeError(f"cannot find opening brace near line {start_line}")

    depth = 0
    end = None

    for i in range(open_brace, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end is not None:
            break

    if end is None:
        raise RuntimeError(f"cannot find function end from line {start_line}")

    return start_idx, end


def join_statements(lines, base_line):
    statements = []
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
            statements.append((start_line, " ".join(current)))
            current = []
            start_line = None

    return statements


def eval_expr(expr):
    expr = expr.strip()
    expr = expr.replace("(", " ").replace(")", " ")
    parts = re.split(r"(\*|\+|-)", expr)

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
    typ = typ.strip()
    typ = typ.replace("const ", "")
    typ = typ.replace("MLD_ALIGN ", "")

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

    # Fallbacks for internal ML-DSA names.
    if typ == "mld_polymat":
        return 16384
    if "polyvecl" in typ or "polyveck" in typ or typ.endswith("vec"):
        return 4096
    if typ == "mld_poly":
        return 1024

    return None


def estimate_size(typ, count_expr=None):
    base = elem_size(typ)
    if base is None:
        return None

    if count_expr is None:
        return base

    count = eval_expr(count_expr)
    if count is None:
        return None

    return base * count


def first_last_usage(function_lines, name, base_line):
    pat = re.compile(r"\b" + re.escape(name) + r"\b")
    hits = []

    for idx, line in enumerate(function_lines):
        if pat.search(line):
            hits.append(base_line + idx)

    if not hits:
        return "", ""

    return min(hits), max(hits)


def parse_statement(stmt):
    s = stmt.strip()
    s = s.replace("MLD_ALIGN ", "")
    s = re.sub(r"\bstatic\b", "", s).strip()

    # MLD_ALLOC(name, type, count, context)
    m = re.search(
        r"MLD_ALLOC\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([^,]+)\s*,",
        s,
    )
    if m:
        name, typ, count = m.group(1), m.group(2), m.group(3)
        return typ, name, count, "MLD_ALLOC"

    # Matrix workspace macros from previous versions.
    m = re.search(
        r"MLD_V17B_ALLOC_MAT\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)",
        s,
    )
    if m:
        return "mld_polymat *", m.group(1), None, "workspace_pointer"

    # type name[count]
    m = re.match(
        r"(?:const\s+)?([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]+)\s*\]",
        s,
    )
    if m:
        return m.group(1), m.group(2), m.group(3), "array"

    # type *name
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

    for line_no, stmt in join_statements(function_lines, base_line):
        parsed = parse_statement(stmt)

        if parsed is None:
            continue

        typ, name, count, kind = parsed

        if kind in ("pointer", "workspace_pointer"):
            size = 8
        else:
            size = estimate_size(typ, count)

        first, last = first_last_usage(function_lines, name, base_line)

        rows.append({
            "line": line_no,
            "name": name,
            "type": typ if count is None else f"{typ}[{count}]",
            "kind": kind,
            "bytes": size,
            "first_use": first,
            "last_use": last,
            "source": stmt,
        })

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


def safe_name(name):
    return name.replace("/", "_").replace(" ", "_")


def write_function_reports(stack_row):
    source_file = stack_row["source_file"]
    variant = stack_row["variant"]
    target = stack_row["target"]

    raw = source_file.read_text()
    clean = strip_comments(raw)
    lines = clean.splitlines(keepends=True)

    start_idx, end_idx = find_function_by_start_line(lines, stack_row["line"])
    function_lines = lines[start_idx:end_idx + 1]
    base_line = start_idx + 1

    locals_found = collect_locals(function_lines, base_line)

    known_non_pointer_total = sum(
        row["bytes"] or 0
        for row in locals_found
        if row["kind"] not in ("pointer", "workspace_pointer")
    )

    unknown = [row for row in locals_found if row["bytes"] is None]

    large = sorted(
        locals_found,
        key=lambda row: row["bytes"] if row["bytes"] is not None else -1,
        reverse=True,
    )

    candidates = []
    big_buffers = [
        row for row in large
        if row["bytes"] is not None and row["bytes"] >= 512 and row["first_use"] and row["last_use"]
    ]

    for i in range(len(big_buffers)):
        for j in range(i + 1, len(big_buffers)):
            a = big_buffers[i]
            b = big_buffers[j]

            if not overlap(a, b):
                candidates.append((a, b))

    csv_path = RESULTS / f"v23a_{target}_lifetime_map_{variant}.csv"
    md_path = RESULTS / f"v23a_{target}_lifetime_map_{variant}.md"
    src_dump_path = RESULTS / f"v23a_{target}_source_{variant}.txt"

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "target", "variant", "stack_bytes", "stack_kind",
                "line", "name", "type", "kind", "bytes",
                "first_use", "last_use", "source"
            ],
        )
        writer.writeheader()
        for row in locals_found:
            out = dict(row)
            out["target"] = target
            out["variant"] = variant
            out["stack_bytes"] = stack_row["stack_bytes"]
            out["stack_kind"] = stack_row["stack_kind"]
            writer.writerow(out)

    with src_dump_path.open("w") as f:
        for i in range(start_idx, end_idx + 1):
            f.write(f"{i + 1:6d}\t{lines[i]}")

    with md_path.open("w") as f:
        f.write(f"# v23a {target} lifetime map: {variant}\n\n")
        f.write(f"Source: `{source_file}`\n\n")
        f.write(f"Compiler symbol: `{stack_row['function']}`\n\n")
        f.write(f"Function range: lines {start_idx + 1}-{end_idx + 1}\n\n")
        f.write(f"Compiler stack frame: **{stack_row['stack_bytes']} B** `{stack_row['stack_kind']}`\n\n")

        f.write("## Local buffers\n\n")
        f.write("| Name | Type | Kind | Approx bytes | First use | Last use | Decl line |\n")
        f.write("|---|---|---|---:|---:|---:|---:|\n")

        for row in large:
            f.write(
                f"| `{row['name']}` | `{row['type']}` | {row['kind']} | "
                f"{row['bytes'] if row['bytes'] is not None else ''} | "
                f"{row['first_use']} | {row['last_use']} | {row['line']} |\n"
            )

        f.write("\n")
        f.write(f"Known non-pointer local total: **{known_non_pointer_total} B**\n\n")

        if unknown:
            f.write("## Unknown-size locals\n\n")
            f.write("| Name | Type | Kind | Decl line | Source |\n")
            f.write("|---|---|---|---:|---|\n")
            for row in unknown:
                f.write(
                    f"| `{row['name']}` | `{row['type']}` | {row['kind']} | "
                    f"{row['line']} | `{row['source']}` |\n"
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

        f.write("\n## Interpretation reminder\n\n")
        f.write(
            "This is a source-level attribution map. The compiler `.su` stack report "
            "remains the source for actual frame size. Use this output to decide what "
            "v23b should move into caller-provided keygen/provisioning workspace.\n"
        )

    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")
    print(f"wrote {src_dump_path}")


def main():
    RESULTS.mkdir(exist_ok=True)

    rows = load_target_stack_rows()

    if not rows:
        raise SystemExit("no keypair_internal or pk_from_sk rows found in .su files")

    for row in rows:
        write_function_reports(row)


if __name__ == "__main__":
    main()
