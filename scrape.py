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
    for element in soup(["script", "style", "footer", "header", "nav", "aside", "form", "button"]):
        element.decompose()
    for tag in soup.find_all(True):
        tag.append(" | ") 

    text = soup.get_text(separator=" ")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def split_dom_content(dom_content, max_length=4000):
    return [dom_content[i : i + max_length] for i in range(0, len(dom_content), max_length)]