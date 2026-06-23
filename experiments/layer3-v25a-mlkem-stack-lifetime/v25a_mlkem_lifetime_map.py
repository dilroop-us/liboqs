#!/usr/bin/env python3
from pathlib import Path
import csv
import re

ROOT = Path.home() / "pqc/liboqs"
RESULTS = ROOT / "layer3-results"
OUT_MD = RESULTS / "v25a_mlkem_lifetime_map.md"
STACK_CSV = RESULTS / "v25a_mlkem_only_mlkem_stack_usage.csv"

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

FUNCTIONS = [
    "indcpa_keypair_derand",
    "indcpa_enc",
    "indcpa_dec",
]

ENV = {
    "MLKEM_K": 3,
    "MLKEM_N": 256,
    "MLKEM_SYMBYTES": 32,
    "MLKEM_SSBYTES": 32,
    "MLKEM_INDCPA_MSGBYTES": 32,
    "MLKEM_INDCPA_PUBLICKEYBYTES": 1184,
    "MLKEM_INDCPA_SECRETKEYBYTES": 1152,
    "MLKEM_INDCPA_BYTES": 1088,
    "MLKEM_POLYBYTES": 384,
    "MLKEM_POLYVECBYTES": 1152,
    "MLKEM_POLYCOMPRESSEDBYTES": 128,
    "MLKEM_POLYVECCOMPRESSEDBYTES": 960,

    "KYBER_K": 3,
    "KYBER_N": 256,
    "KYBER_SYMBYTES": 32,
    "KYBER_SSBYTES": 32,
    "KYBER_INDCPA_MSGBYTES": 32,
    "KYBER_INDCPA_PUBLICKEYBYTES": 1184,
    "KYBER_INDCPA_SECRETKEYBYTES": 1152,
    "KYBER_INDCPA_BYTES": 1088,
    "KYBER_POLYBYTES": 384,
    "KYBER_POLYVECBYTES": 1152,
    "KYBER_POLYCOMPRESSEDBYTES": 128,
    "KYBER_POLYVECCOMPRESSEDBYTES": 960,
}

TYPE_BYTES = {
    "poly": 512,
    "polyvec": 1536,
    "mlk_poly": 512,
    "mlk_polyvec": 1536,

    # ML-KEM-768 matrix: K x K polys = 3 x 3 x 512 B
    "mlk_polymat": 4608,

    # Approximate cache size. Compiler frame confirms this is close enough
    # for workspace planning; exact frame also includes alignment/spills.
    "mlk_polyvec_mulcache": 768,

    "uint8_t": 1,
    "int16_t": 2,
}


def safe_eval(expr: str) -> int:
    expr = expr.strip()

    for key, value in ENV.items():
        expr = re.sub(rf"\b{re.escape(key)}\b", str(value), expr)

    expr = expr.replace(" ", "")

    if not re.fullmatch(r"[0-9+\-*/%()]+", expr):
        return 0

    try:
        return int(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return 0


def load_stack_frames():
    frames = {}

    if not STACK_CSV.exists():
        return frames

    with STACK_CSV.open() as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                row["bytes"] = int(row["bytes"])
            except Exception:
                continue

            frames[(row["variant"], row["function"])] = row

    return frames


def extract_function_body(text: str, fn_name: str):
    search_pos = 0

    while True:
        idx = text.find(fn_name, search_pos)

        if idx == -1:
            return None

        brace = text.find("{", idx)

        if brace == -1:
            return None

        between = text[idx:brace]

        if ";" in between:
            search_pos = idx + len(fn_name)
            continue

        depth = 0

        for pos in range(brace, len(text)):
            ch = text[pos]

            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1

                if depth == 0:
                    fn_start_line = text[:idx].count("\n") + 1
                    body_start_line = text[:brace].count("\n") + 1
                    fn_end_line = text[:pos].count("\n") + 1
                    body = text[brace + 1:pos]
                    return body, fn_start_line, body_start_line, fn_end_line

        return None


def statementize(body: str, body_start_line: int):
    statements = []
    current = []
    start_line = body_start_line

    for offset, raw in enumerate(body.splitlines(), 1):
        line_no = body_start_line + offset
        line = raw.split("//", 1)[0].strip()

        if not line:
            continue

        if not current:
            start_line = line_no

        current.append(line)

        if ";" in line:
            stmt = " ".join(current)
            statements.append((start_line, stmt))
            current = []

    return statements


def split_declarators(rest: str):
    parts = []
    current = []
    bracket = 0
    paren = 0

    for ch in rest:
        if ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
        elif ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1

        if ch == "," and bracket == 0 and paren == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)

    if current:
        parts.append("".join(current).strip())

    return parts


def clean_declarator(decl: str):
    decl = decl.split("=", 1)[0].strip()
    decl = re.sub(r"__attribute__\s*\(\(.*?\)\)", "", decl).strip()

    pointer = "*" in decl
    decl_no_ptr = decl.replace("*", " ").strip()

    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[(.*?)\])?$", decl_no_ptr)

    if not m:
        return None

    return m.group(1), m.group(2), pointer


def estimate_size(type_name: str, count_expr: str | None, pointer: bool):
    if pointer:
        return 8

    base = TYPE_BYTES.get(type_name, 0)

    if base == 0:
        return 0

    if count_expr is None:
        return base

    count = safe_eval(count_expr)

    if count == 0:
        return 0

    return base * count


def find_lifetime(body_lines, body_start_line, name):
    first = None
    last = None
    pat = re.compile(rf"\b{re.escape(name)}\b")

    for offset, line in enumerate(body_lines, 1):
        global_line = body_start_line + offset

        if pat.search(line):
            if first is None:
                first = global_line
            last = global_line

    return first or 0, last or 0


def scan_alloc_macros(stmts, body_lines, body_start_line):
    rows = []
    seen = set()

    alloc_re = re.compile(
        r"\b(?:MLKEM_ALLOC|MLK_ALLOC|KYBER_ALLOC)\s*"
        r"\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
        r"([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
        r"([^,]+)\s*,"
    )

    for decl_line, stmt in stmts:
        m = alloc_re.search(stmt)

        if not m:
            continue

        name = m.group(1)
        type_name = m.group(2)
        count_expr = m.group(3).strip()

        if name in seen:
            continue

        seen.add(name)

        approx = estimate_size(type_name, count_expr, False)
        first, last = find_lifetime(body_lines, body_start_line, name)

        rows.append(
            {
                "name": name,
                "type": f"{type_name}[{count_expr}]",
                "kind": "ALLOC_MACRO",
                "approx_bytes": approx,
                "decl_line": decl_line,
                "first_use": first,
                "last_use": last,
            }
        )

    return rows


def scan_plain_decls(stmts, body_lines, body_start_line):
    rows = []
    seen = set()

    decl_re = re.compile(
        r"^\s*"
        r"(?:(?:[A-Z][A-Z0-9_]*\s*(?:\([^;]*?\))?)\s+)*"
        r"(?:(?:static|volatile|const|register)\s+)*"
        r"(mlk_polyvec|mlk_poly|polyvec|poly|uint8_t|int16_t)\s+"
        r"(.+?)\s*;"
    )

    for decl_line, stmt in stmts:
        # Skip allocation macro statements here. They are handled separately.
        if "ALLOC" in stmt:
            continue

        m = decl_re.match(stmt)

        if not m:
            continue

        type_name = m.group(1)
        rest = m.group(2)

        for decl in split_declarators(rest):
            parsed = clean_declarator(decl)

            if parsed is None:
                continue

            name, count_expr, pointer = parsed

            if name in seen:
                continue

            seen.add(name)

            approx = estimate_size(type_name, count_expr, pointer)
            first, last = find_lifetime(body_lines, body_start_line, name)

            if pointer:
                kind = "pointer"
                type_repr = f"{type_name} *"
            elif count_expr:
                kind = "local_array"
                type_repr = f"{type_name}[{count_expr}]"
            else:
                kind = "local_object"
                type_repr = type_name

            rows.append(
                {
                    "name": name,
                    "type": type_repr,
                    "kind": kind,
                    "approx_bytes": approx,
                    "decl_line": decl_line,
                    "first_use": first,
                    "last_use": last,
                }
            )

    return rows


def scan_locals(body: str, body_start_line: int):
    body_lines = body.splitlines()
    stmts = statementize(body, body_start_line)

    rows = []
    rows.extend(scan_alloc_macros(stmts, body_lines, body_start_line))
    rows.extend(scan_plain_decls(stmts, body_lines, body_start_line))

    # Deduplicate by name, keeping larger estimate if duplicate appears.
    best = {}

    for row in rows:
        old = best.get(row["name"])

        if old is None or row["approx_bytes"] > old["approx_bytes"]:
            best[row["name"]] = row

    rows = list(best.values())
    rows.sort(key=lambda r: r["approx_bytes"], reverse=True)
    return rows


def function_symbol(prefix: str, fn: str):
    return f"{prefix}_{fn}"


frames = load_stack_frames()

md = "# v25a ML-KEM lifetime map for indcpa.c\n\n"
md += "This map scans local variables and ML-KEM allocation macros inside function bodies.\n\n"
md += "Assumptions for ML-KEM-768:\n\n"
md += "- `poly` / `mlk_poly` estimated as 512 B\n"
md += "- `polyvec` / `mlk_polyvec` estimated as 1536 B\n"
md += "- `MLKEM_K = 3`\n\n"

for variant, path, prefix in TARGETS:
    text = path.read_text()
    all_lines = text.splitlines()

    md += f"## {variant}\n\n"
    md += f"Source: `{path}`\n\n"

    source_dump = []

    for fn in FUNCTIONS:
        extracted = extract_function_body(text, fn)

        if extracted is None:
            md += f"### {fn}\n\nCould not extract function body.\n\n"
            continue

        body, fn_start_line, body_start_line, fn_end_line = extracted
        rows = scan_locals(body, body_start_line)

        symbol = function_symbol(prefix, fn)
        frame = frames.get((variant, symbol), {})
        frame_bytes = frame.get("bytes", 0)
        frame_kind = frame.get("kind", "unknown")

        md += f"### {fn}\n\n"
        md += f"Compiler symbol: `{symbol}`\n\n"
        md += f"Function range: lines {fn_start_line}-{fn_end_line}\n\n"
        md += f"Compiler stack frame: **{frame_bytes} B** `{frame_kind}`\n\n"

        source_dump.append(f"# {variant} {fn} lines {fn_start_line}-{fn_end_line}\n")
        for line_no in range(fn_start_line, fn_end_line + 1):
            if 1 <= line_no <= len(all_lines):
                source_dump.append(f"{line_no:6d}\t{all_lines[line_no - 1]}\n")
        source_dump.append("\n")

        if not rows:
            md += "No local buffers detected by scanner.\n\n"
            continue

        md += "## Local buffers\n\n"
        md += "| Name | Type | Kind | Approx bytes | First use | Last use | Decl line |\n"
        md += "|---|---|---|---:|---:|---:|---:|\n"

        for r in rows:
            md += (
                f"| `{r['name']}` | `{r['type']}` | {r['kind']} | "
                f"{r['approx_bytes']} | {r['first_use']} | {r['last_use']} | {r['decl_line']} |\n"
            )

        known_total = sum(r["approx_bytes"] for r in rows if r["kind"] != "pointer")
        pointer_total = sum(r["approx_bytes"] for r in rows if r["kind"] == "pointer")

        md += f"\nKnown non-pointer local total: **{known_total} B**\n\n"
        md += f"Pointer local total: **{pointer_total} B**\n\n"

        if frame_bytes and known_total < frame_bytes // 2:
            md += (
                "Scanner warning: detected local-buffer total is much smaller than compiler frame. "
                "Inspect source dump before using this map for patch design.\n\n"
            )

    src_out = RESULTS / f"v25a_mlkem_indcpa_source_{variant}.txt"
    src_out.write_text("".join(source_dump))

md += "## v25a conclusion\n\n"
md += (
    "The compiler `.su` stack report remains the source of truth for actual frame size. "
    "This source map is used to attribute the frame to local buffers and plan caller-workspace structs.\n"
)

OUT_MD.write_text(md)

print(f"wrote {OUT_MD}")
print("wrote source dumps:")
print(RESULTS / "v25a_mlkem_indcpa_source_x86_64.txt")
print(RESULTS / "v25a_mlkem_indcpa_source_ref.txt")
