import selenium.webdriver as webdriver 
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
def Scrape_website(website):
    print("Lanching Chrome Browser")
    chrome_driver_path="./chromedriver.exe"
    OPTION = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(chrome_driver_path),options=OPTION)
    try :
        driver.get(website)
        print("Page loaded ... ")
        return driver.page_source
    finally :
        driver.quit()

def extract_body_content(html_content):
    soup = BeautifulSoup(html_content,"html.parser")
    body_content = soup.body
    if body_content:
        return str(body_content)
    return ""
def clean_body_content(body_content):
    soup = BeautifulSoup(body_content,"html.parser")
    
    for script_or_style in soup(["script","style"]):
        script_or_style.extract()
    cleaned_content = soup.get_text(separator="\n")
    cleaned_content = "\n".join(line.strip() for line in cleaned_content.splitlines() if line.split())
    return cleaned_content