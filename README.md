# Collecty

![demo](docs/demo.gif)

An Intelligent, Agentic Web Scraping Framework for Automated Schema Discovery and Structural Analysis.

## About

Collecty is a Python-based framework designed to intelligently scrape websites. Its core innovation lies in its "agentic" approach, meaning it can autonomously discover and analyze the structure of the data it encounters, rather than just extracting based on pre-defined, static rules. This makes it particularly powerful for projects requiring automated schema discovery from web pages.

Collecty is a Streamlit app: enter a URL, and it scrapes the site, suggests relevant data columns using an LLM, and extracts a clean, structured table you can download as CSV.

## Key Features

*   **Multi-Page Scraping:** Automatically follows "next page" links (pagination) to scrape up to 10 pages of a site in one run.
*   **Intelligent Scraping:** Leverages Selenium with headless Chrome to navigate and extract data from complex, JavaScript-heavy web structures.
*   **Automated Schema Discovery:** A cloud LLM (via the Groq API) analyzes the page content and automatically suggests the most relevant data columns.
*   **Consistent Extraction:** A shared *format contract* is built once per run and injected into every parallel chunk prompt, and a final *harmonization* pass rewrites every value to match it — so a price is always `1000`, never `1k$` in one chunk and `1000$` in another. Deterministic normalization (`1k` → `1000`, `1,200 $` → `1200`) catches the rest.
*   **Structural Analysis:** Analyzes the layout and patterns within HTML to inform the extraction process.
*   **Python-Based:** Built entirely with Python, ensuring ease of use and integration into existing data science or automation workflows.

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3 (The project is 100% Python)
*   `pip` (Python package installer)
*   A Chrome browser
*   A Groq API key (free at [console.groq.com](https://console.groq.com))

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/loueylahwel/Collecty.git
    cd Collecty
    ```

2.  **Install dependencies**
    The project dependencies are listed in `requirements.txt`. Install them using pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the Groq API key**
    ```bash
    cp .env.example .env
    ```
    Then edit `.env` and set `GROQ_API_KEY` to your key from [console.groq.com](https://console.groq.com). You can optionally override `GROQ_MODEL` (defaults to `llama-3.3-70b-versatile`). If no key is configured, the app lets you paste one into the sidebar at runtime.

4.  **ChromeDriver (usually nothing to do)**
    Modern Selenium (>= 4.6) includes Selenium Manager, which automatically resolves the correct driver for your installed Chrome — no manual setup needed. The bundled `chromedriver.exe` is kept in the repository only as a fallback for older setups.

## Usage

Run the Streamlit app:

```bash
streamlit run main.py
```

A typical workflow:

1.  **Enter a URL** and (optionally) set **Pages to scrape** in the sidebar to follow pagination.
2.  **Step 1: Scrape Site** — scrapes the page(s) and suggests columns.
3.  **Step 2: Select Columns** — keep or trim the suggested columns, add extra instructions (e.g. "Translate to English").
4.  **Step 3: Generate Structured Table** — extracts the data in parallel, normalizes and harmonizes it, and shows the result as a table with a CSV download.

The project is structured into several core Python scripts:

*   `main.py`: The Streamlit user interface (entry point).
*   `scrape.py`: Selenium-based scraping, pagination detection, and DOM cleaning/chunking.
*   `parse.py`: Groq-powered column suggestion, contract-based parallel extraction, deterministic normalization, and table harmonization.

## Contributing

This is an active project. Feel free to fork the repository and submit pull requests.

## License

This project does not currently specify a license. You may need to contact the repository owner for permission to use or distribute this code.

## Contact

For questions or feedback, please open an issue on the GitHub repository.
