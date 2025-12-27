import streamlit as st
from scrape import *
from parse import *

st.set_page_config(page_title="Collecty", layout="wide")
st.title("COLLECTY")

url = st.text_input("Enter Website URL:")

if st.button("Scrape Site"):
    if url:
        with st.spinner("Extracting Website Source..."):
            res = Scrape_website(url)
            st.session_state.dom_content = clean_body_content(extract_body_content(res))
            st.success("Website Scraped Successfully!")

if "dom_content" in st.session_state:
    parse_description = st.text_area("What do you want to extract?")

    if st.button("Generate Structured Table"):
        if parse_description:
            with st.spinner("Standardizing and Parsing Data..."):
                dom_chunks = split_dom_content(st.session_state.dom_content)
                parsed_result = parse_with_ollama(dom_chunks, parse_description)
                st.subheader("Final Data Table")
                st.markdown(parsed_result)
                st.download_button("Download as CSV", parsed_result.replace(" | ", ","), "extracted_data.csv")