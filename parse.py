import os
import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

load_dotenv()

HARMONIZE_BLOCK_LIMIT = 12000

_model = None


def _get_model():
    """Create the ChatGroq model lazily so importing this module never
    requires an API key. Raises a clear error only on actual use."""
    global _model
    if _model is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Get a key at https://console.groq.com "
                "and put it in your .env file or environment."
            )
        _model = ChatGroq(
            model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0,
            api_key=api_key,
        )
    return _model


def _to_text(res):
    """Chat models return AIMessage; plain LLMs return str."""
    return res.content if hasattr(res, "content") else res


def suggest_columns(sample_content):
    prompt = ChatPromptTemplate.from_template(
        "Based on this website text: {sample_content}\n"
        "Return ONLY a comma-separated list of the 5-7 most relevant data columns found. No extra text."
    )
    chain = prompt | _get_model()
    res = chain.invoke({"sample_content": sample_content})
    return [c.strip() for c in _to_text(res).split(",") if c.strip()]


def build_format_contract(columns, sample):
    """ONE LLM call producing a short, shared format spec: for each selected
    column, the exact canonical output format. Passed to every chunk parser
    so formats don't drift between chunks."""
    prompt = ChatPromptTemplate.from_template(
        "You are defining a strict output format contract for a data extraction pipeline.\n"
        "Selected columns: {columns}\n"
        "Sample of the source text:\n{sample}\n\n"
        "For EACH column, write ONE short line 'ColumnName: exact canonical output format'. "
        "Be explicit and unambiguous. Examples: "
        "Price -> number only, plain digits, no currency symbol, no thousands separators, "
        "no k/m abbreviations (write 1k as 1000); "
        "Date -> YYYY-MM-DD; Rating -> number 0-5. "
        "End with: Missing values must be written as N/A. Keep the whole contract short."
    )
    chain = prompt | _get_model()
    res = chain.invoke({"columns": ", ".join(columns), "sample": sample[:2000]})
    return _to_text(res).strip()


_NA_EXACT = {"", "n/a", "na", "-", "--", "none", "null", "unknown", "non spécifié", "non specifie"}

_MULTIPLIERS = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}


def normalize_value(val, col_name):
    """Deterministic value normalization (no LLM).

    - missing markers -> "N/A"
    - strips currency symbols ($, EUR signs, GBP) and currency codes (USD/EUR/DZD/DT/...)
    - "1,200" / "1 200" thousands separators -> "1200"
    - k/K/m/M/b/B suffixes expanded: 1k -> 1000, 2.5m -> 2500000
    - non-numeric values returned stripped, unchanged
    """
    v = val.strip()
    low = v.lower()
    if low in _NA_EXACT or "non spécifié" in low or "non specifie" in low:
        return "N/A"

    cleaned = re.sub(r"[$€£]", "", v)
    cleaned = re.sub(
        r"\b(USD|EUR|DZD|DT|GBP|CAD|MAD|TND|CHF|JPY)\b", "", cleaned, flags=re.IGNORECASE
    ).strip()

    m = re.fullmatch(r"(-?[\d][\d\s,.]*?)\s*([kKmMbB]?)", cleaned)
    if not m or not re.search(r"\d", m.group(1)):
        return v  # non-numeric: stripped, unchanged

    num_part, suffix = m.group(1).strip(), m.group(2).lower()

    # Unify thousands separators: "1,000" / "1 000" -> "1000"
    if re.fullmatch(r"-?\d{1,3}([,\s]\d{3})+(\.\d+)?", num_part):
        num_part = re.sub(r"[,\s]", "", num_part)
    else:
        num_part = num_part.replace(" ", "")
        # decimal comma: "12,5" -> "12.5"
        if re.fullmatch(r"-?\d+,\d+", num_part):
            num_part = num_part.replace(",", ".")

    try:
        number = float(num_part)
    except ValueError:
        return v

    number *= _MULTIPLIERS.get(suffix, 1)

    if number == int(number):
        return str(int(number))
    return f"{number:f}".rstrip("0").rstrip(".")


def parse_chunk(chunk, columns, extra_info, contract):
    col_str = " | ".join(columns)
    template = (
        "Context: {dom_content}\n\n"
        "Task: Extract items into these columns: {col_str}\n"
        "Extra Rules: {extra_info}\n\n"
        "FORMAT CONTRACT (apply to every value, exactly):\n{contract}\n\n"
        "GLOBAL RULES (mandatory):\n"
        "- One item per line.\n"
        "- Values separated by ' | '.\n"
        "- Exactly {num_cols} values per line.\n"
        "- No header line, no markdown, no commentary.\n"
        "- Use 'N/A' for missing values.\n"
        "- Never use abbreviations like k/m for numbers (write 1k as 1000)."
    )
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | _get_model()
    return chain.invoke(
        {
            "dom_content": chunk,
            "col_str": col_str,
            "extra_info": extra_info,
            "contract": contract,
            "num_cols": len(columns),
        }
    )


def harmonize_table(df, contract):
    """Final consistency pass: ONE LLM call (or one per <=12000-char block)
    rewrites every value to match the format contract exactly. Falls back to
    the pre-harmonization DataFrame if anything goes wrong."""
    if df.empty:
        return df

    header = " | ".join(df.columns)
    all_rows = [" | ".join(str(v) for v in row) for row in df.itertuples(index=False, name=None)]

    blocks, current, current_len = [], [], len(header)
    for row in all_rows:
        if current and current_len + len(row) + 1 > HARMONIZE_BLOCK_LIMIT:
            blocks.append(current)
            current, current_len = [], len(header)
        current.append(row)
        current_len += len(row) + 1
    if current:
        blocks.append(current)

    prompt = ChatPromptTemplate.from_template(
        "Here is a table and a format contract.\n\n"
        "FORMAT CONTRACT:\n{contract}\n\n"
        "TABLE (columns: {header}):\n{table}\n\n"
        "Rewrite every value to match the contract exactly. Keep all rows and their order. "
        "Output ONLY the table rows in the same pipe format (' | ' separated), "
        "no header line, no markdown, no commentary."
    )

    try:
        model = _get_model()
        chain = prompt | model
        harmonized_lines = []
        for block in blocks:
            res = chain.invoke(
                {"contract": contract, "header": header, "table": "\n".join(block)}
            )
            harmonized_lines.extend(_to_text(res).strip().split("\n"))

        parsed = []
        header_lower = [c.lower() for c in df.columns]
        for line in harmonized_lines:
            line = line.strip()
            if not line or set(line) <= set("-| "):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != len(df.columns):
                continue
            if [p.lower() for p in parts] == header_lower:
                continue
            parsed.append(parts)

        if not parsed:
            return df  # parsing failed: keep pre-harmonization data
        return pd.DataFrame(parsed, columns=df.columns)
    except Exception:
        return df  # any failure: keep pre-harmonization data


def parse_with_groq(dom_chunks, columns, extra_info):
    # 1. Build the shared format contract once, from a sample of the first chunk.
    sample = dom_chunks[0][:2000] if dom_chunks else ""
    contract = build_format_contract(columns, sample)

    # 2. Parse all chunks in parallel, with the contract in every prompt.
    def process_task(item):
        idx, chunk = item
        return (idx, parse_chunk(chunk, columns, extra_info, contract))

    with ThreadPoolExecutor(max_workers=4) as executor:
        indexed_results = list(executor.map(process_task, enumerate(dom_chunks)))
    indexed_results.sort(key=lambda x: x[0])

    # 3. Robust row parsing: exact column count, drop headers/separators, dedupe.
    unique_rows = []
    seen_rows = set()
    header_lower = [c.lower() for c in columns]

    for _, res in indexed_results:
        text = _to_text(res)
        if not text or not text.strip():
            continue
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or set(line) <= set("-| "):
                continue  # drop "----" separator lines
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != len(columns):
                continue  # accept only lines with exactly len(columns) parts
            if [p.lower() for p in parts] == header_lower:
                continue  # drop header repeats
            normalized = tuple(normalize_value(p, columns[i]) for i, p in enumerate(parts))
            if normalized in seen_rows:
                continue
            seen_rows.add(normalized)
            unique_rows.append(list(normalized))

    # 4. DataFrame + final harmonization pass against the contract.
    df = pd.DataFrame(unique_rows, columns=columns)
    return harmonize_table(df, contract)


# Backwards-compatible alias so old imports don't break.
parse_with_ollama = parse_with_groq
