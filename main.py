import streamlit as st
from scrape import *
from parse import *

st.set_page_config(page_title="Collecty | Universal Scraper", layout="wide")
st.title("COLLECTY")

url = st.text_input("Enter Website URL:", placeholder="https://example.com")

if st.button("Step 1: Scrape Site", type="primary"):
    if url:
        with st.spinner("Extracting content..."):
            res = Scrape_website(url)
            if res:
                st.session_state.dom_content = clean_body_content(extract_body_content(res))
                st.success(f"Website Scraped!")
                
                # Analyze structure to suggest columns
                with st.spinner("Suggesting columns..."):
                    sample = st.session_state.dom_content[:4000]
                    cols = suggest_columns(sample)
                    st.session_state.suggested_cols = cols
            else:
                st.error("Failed to retrieve content.")

if "dom_content" in st.session_state:
    st.divider()
    
    # Checkbox/Multiselect for columns
    options = st.session_state.get("suggested_cols", ["Product Name", "Price"])
    selected_cols = st.multiselect("Step 2: Select Columns to Extract", options, default=options)
    
    extra_info = st.text_input("Extra Instructions (Optional)", placeholder="e.g. Translate to English, keep only ASUS brands")

    if st.button("Step 3: Generate Structured Table"):
        if selected_cols:
            with st.spinner("Parsing data..."):
                dom_chunks = split_dom_content(st.session_state.dom_content)
                # Pass only the selected columns
                parsed_result = parse_with_ollama(dom_chunks, selected_cols, extra_info)
                
                st.subheader("Final Data Table")
                st.markdown(parsed_result)
                
                csv_data = parsed_result.replace(" | ", ",")
                st.download_button(" Download CSV", csv_data, "data.csv", "text/csv")
        else:
            st.warning("Please select at least one column.")