import selenium.webdriver as webdriver 
from selenium.webdriver.chrome.service import Service
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
