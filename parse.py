import re
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from concurrent.futures import ThreadPoolExecutor

model = OllamaLLM(model="qwen3-coder:480b-cloud", request_timeout=300.0)

def suggest_columns(sample_content):
    prompt = ChatPromptTemplate.from_template(
        "Based on this website text: {sample_content}\n"
        "Return ONLY a comma-separated list of the 5-7 most relevant data columns found. No extra text."
    )
    chain = prompt | model
    res = chain.invoke({"sample_content": sample_content})
    return [c.strip() for c in res.split(",") if c.strip()]

def normalize_value(val, col_name):
    v_clean = val.strip()
    if any(p in v_clean.lower() for p in ["non spécifié", "n/a", "unknown"]):
        return "N/A"

    match = re.search(r'([\d\s,]+)', v_clean)
    if match:
        num_str = re.sub(r'[^\d]', '', match.group(1))
        if num_str and float(num_str) > 100000:
            scaled = int(float(num_str) / 1000)
            return v_clean.replace(match.group(1).strip(), f"{scaled:,}".replace(",", " "))
    return v_clean

def parse_chunk(chunk, columns, extra_info):
    col_str = " | ".join(columns)
    template = (
        "Context: {dom_content}\n\n"
        "Task: Extract items into these columns: {col_str}\n"
        "Extra Rules: {extra_info}\n"
        "Constraint: Return ONLY raw data rows. DO NOT include the header names or '---' separators. "
        "Each line must be: Value1 | Value2 | Value3"
    )
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model
    return chain.invoke({"dom_content": chunk, "col_str": col_str, "extra_info": extra_info})

def parse_with_ollama(dom_chunks, columns, extra_info):
    total_chunks = len(dom_chunks)
    indexed_results = []

    def process_task(item):
        idx, chunk = item
        res = parse_chunk(chunk, columns, extra_info)
        return (idx, res)

    with ThreadPoolExecutor(max_workers=4) as executor:
        indexed_results = list(executor.map(process_task, enumerate(dom_chunks)))

    indexed_results.sort(key=lambda x: x[0])
    
    unique_rows = []
    seen_rows = set()

    for _, res in indexed_results:
        if res and res.strip():
            for line in res.strip().split('\n'):
                if any(col in line for col in columns) and "|" in line:
                    if line.count("|") != len(columns) - 1: continue 
                
                parts = [p.strip() for p in line.split('|')]
                if len(parts) == len(columns):
                    normalized = [normalize_value(p, columns[i]) for i, p in enumerate(parts)]
                    row_string = " | ".join(normalized)
                    # Filter out header repeats
                    if row_string.lower() == " | ".join(columns).lower(): continue
                    
                    if row_string not in seen_rows:
                        unique_rows.append(row_string)
                        seen_rows.add(row_string)
    
    # Construct final table ONCE
    header = " | ".join(columns)
    sep = " | ".join(["---"] * len(columns))
    return f"{header}\n{sep}\n" + "\n".join(unique_rows)