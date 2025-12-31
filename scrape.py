import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def Scrape_website(website):
    chrome_driver_path = "./chromedriver.exe"
    options = Options()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
    try:
        driver.get(website)
        driver.implicitly_wait(10)
        return driver.page_source
    except:
        return ""
    finally:
        driver.quit()

def extract_body_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return str(soup.body) if soup.body else ""

def clean_body_content(body_content):
    soup = BeautifulSoup(body_content, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "svg", "form"]):
        element.decompose()

    # Crucial for column detection: Ensure titles and data stay on separate conceptual lines
    for tag in soup.find_all(['div', 'tr', 'li', 'p', 'h1', 'h2', 'h3', 'span']):
        tag.append(" | ") 

    text = soup.get_text(separator=" ")
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 1]
    return " ".join(lines)

def split_dom_content(dom_content, max_length=5000, overlap=500):
    chunks = []
    i = 0
    while i < len(dom_content):
        chunks.append(dom_content[i : i + max_length])
        i += (max_length - overlap)
        if i >= len(dom_content): break
    return chunks