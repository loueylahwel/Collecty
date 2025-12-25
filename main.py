import streamlit as st
from scrape import Scrape_website
st.title("Web Scraper")
url = st.text_input("Enter Website URL : ")
if st.button("Scrape Site") :
    if url:
        st.write("Scraping the Website...")
        res = Scrape_website(url)
        print(res)