import os

import streamlit as st
from dotenv import load_dotenv

from scrape import *
from parse import *

load_dotenv()

st.set_page_config(page_title="Collecty | Universal Scraper", layout="wide")
st.title("COLLECTY")

with st.sidebar:
    st.header("Settings")
    max_pages = st.slider(
        "Pages to scrape",
        min_value=1,
        max_value=10,
        value=1,
        help='Follow "next page" links to scrape multiple pages of the same site.',
    )
    if not os.environ.get("GROQ_API_KEY"):
        st.warning("GROQ_API_KEY is not set in the environment.")
        api_key = st.text_input("Groq API key", type="password")
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key

url = st.text_input("Enter Website URL:", placeholder="https://example.com")

if st.button("Step 1: Scrape Site", type="primary"):
    if url:
        with st.spinner("Extracting content..."):
            pages = scrape_multiple_pages(url, max_pages=max_pages)
            if pages:
                cleaned_pages = [
                    clean_body_content(extract_body_content(html)) for _, html in pages
                ]
                st.session_state.dom_content = "\n".join(p for p in cleaned_pages if p)
                st.session_state.scraped_urls = [page_url for page_url, _ in pages]
                st.success(f"Website scraped: {len(pages)} page(s)!")

                # Analyze structure to suggest columns
                with st.spinner("Suggesting columns..."):
                    sample = st.session_state.dom_content[:4000]
                    cols = suggest_columns(sample)
                    st.session_state.suggested_cols = cols
            else:
                st.error("Failed to retrieve content.")

if st.session_state.get("scraped_urls"):
    with st.expander(f"Scraped pages ({len(st.session_state.scraped_urls)})"):
        for page_url in st.session_state.scraped_urls:
            st.write(page_url)

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
                df = parse_with_groq(dom_chunks, selected_cols, extra_info)

                st.subheader("Final Data Table")
                st.dataframe(df, use_container_width=True)
                st.caption(f"{len(df)} row(s)")

                st.download_button(" Download CSV", df.to_csv(index=False), "data.csv", "text/csv")
        else:
            st.warning("Please select at least one column.")
