import os
import time
from urllib.parse import urljoin, urldefrag

import selenium.webdriver as webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


def create_driver():
    """Create a headless Chrome driver.

    Tries Selenium Manager first (Selenium >= 4.6 auto-resolves the driver),
    then falls back to the bundled chromedriver.exe next to this file.
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    try:
        return webdriver.Chrome(options=options)
    except Exception:
        driver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")
        if os.path.exists(driver_path):
            return webdriver.Chrome(service=Service(driver_path), options=options)
        raise


def Scrape_website(website):
    driver = create_driver()
    try:
        driver.get(website)
        driver.implicitly_wait(10)
        return driver.page_source
    except Exception:
        return ""
    finally:
        driver.quit()


def find_next_page_url(html, current_url):
    """Heuristically find the "next page" URL in a page's HTML.

    Returns an absolute URL, or None if no next link is found.
    """
    soup = BeautifulSoup(html, "html.parser")

    candidates = []
    # Strong signals first
    candidates.extend(soup.select('a[rel="next"]'))
    candidates.extend(soup.select('link[rel="next"]'))
    candidates.extend(soup.select("li.next a"))
    candidates.extend(soup.select('.pagination a[aria-label*="Next" i]'))
    # Weaker signals: class/id/aria-label/text containing "next", "»" or "›"
    for a in soup.find_all("a"):
        haystack = " ".join(
            filter(
                None,
                [
                    a.get("class") and " ".join(a.get("class")),
                    a.get("id"),
                    a.get("aria-label"),
                    a.get_text(strip=True),
                ],
            )
        ).lower()
        if "next" in haystack or "»" in haystack or "›" in haystack:
            candidates.append(a)

    current_defrag = urldefrag(current_url)[0]
    for tag in candidates:
        href = tag.get("href")
        if not href:
            continue
        href = href.strip()
        if href.lower().startswith("javascript:"):
            continue
        absolute = urldefrag(urljoin(current_url, href))[0]
        # Skip same-page anchors / self links
        if absolute == current_defrag:
            continue
        return absolute
    return None


def scrape_multiple_pages(start_url, max_pages=1, delay=1.5):
    """Scrape up to max_pages pages, following "next page" links.

    Returns a list of (url, html) tuples. Reuses a single driver and
    always quits it. Stops on: no next link, already-visited next URL
    (loop protection), or max_pages reached.
    """
    results = []
    visited = set()
    url = start_url
    driver = create_driver()
    try:
        for _ in range(max_pages):
            if url in visited:
                break
            visited.add(url)
            driver.get(url)
            driver.implicitly_wait(10)
            html = driver.page_source
            results.append((url, html))

            next_url = find_next_page_url(html, url)
            if not next_url or next_url in visited:
                break
            url = next_url
            time.sleep(delay)
    except Exception:
        pass
    finally:
        driver.quit()
    return results


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

def split_dom_content(dom_content, max_length=5000, overlap=300):
    chunks = []
    i = 0
    while i < len(dom_content):
        chunks.append(dom_content[i : i + max_length])
        i += (max_length - overlap)
        if i >= len(dom_content): break
    return chunks
