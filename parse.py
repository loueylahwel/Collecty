from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from concurrent.futures import ThreadPoolExecutor

model = OllamaLLM(
    model="qwen2.5:7b",
    request_timeout=300.0
)

def get_extraction_columns(parse_description):
    column_prompt = ChatPromptTemplate.from_template(
        "Based on this user request: '{parse_description}', identify the specific data columns needed. "
        "Return ONLY a comma-separated list of column names. No other text."
    )
    chain = column_prompt | model
    response = chain.invoke({"parse_description": parse_description})
    return [c.strip() for c in response.split(',') if c.strip()]

def parse_chunk(chunk, columns):
    col_str = " | ".join(columns)
    template = (
        "Context: {dom_content}\n"
        "Task: Extract data into these columns: {col_str}\n"
        "Formatting Rules:\n"
        "1. FORMAT: Value1 | Value2 | Value3\n"
        "2. CONSISTENCY: Use the same units for all rows (e.g., if one RAM is '16GB', all should be '16GB', not '1600MHz').\n"
        "3. MISSING DATA: If a specific field is missing, use 'N/A'. Never leave a cell empty.\n"
        "4. NO HEADERS: Return only raw data rows.\n"
        "5. CLEANING: Remove extra symbols like 'DT' or 'Go' if they are inconsistent; keep only the core value if possible."
    )
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model
    return chain.invoke({"dom_content": chunk, "col_str": col_str})

def parse_with_ollama(dom_chunks, parse_description):
    columns = get_extraction_columns(parse_description)
    total_chunks = len(dom_chunks)
    counter = 0

    def process_with_counter(index_chunk_tuple):
        idx, chunk = index_chunk_tuple
        result = parse_chunk(chunk, columns)
        print(f"Progress: {idx + 1}/{total_chunks} chunks processed")
        return result
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(process_with_counter, enumerate(dom_chunks)))

    rows = []
    for res in results:
        if res and res.strip():
            for line in res.strip().split('\n'):
                if line.count('|') == len(columns) - 1:
                    rows.append(line.strip())
    
    header = " | ".join(columns)
    separator = " | ".join(["---"] * len(columns))
    return f"{header}\n{separator}\n" + "\n".join(rows)