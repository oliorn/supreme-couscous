import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def normalize_url(url: str) -> str:
    # ef notandinn skrifar bara "visir.is" þá bætum við https:// fyrir framan
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    return url

def scrape_company(url: str):
    url = normalize_url(url)
    """Scrape basic company information from a website."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Failed to fetch URL: {str(e)}"}

    soup = BeautifulSoup(response.text, "html.parser")

    # Basic info extraction
    title = soup.title.string.strip() if soup.title else ""
    description = ""
    keywords = ""
    about_text = ""

    # Meta tags
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag and desc_tag.get("content"):
        description = desc_tag["content"].strip()

    kw_tag = soup.find("meta", attrs={"name": "keywords"})
    if kw_tag and kw_tag.get("content"):
        keywords = kw_tag["content"].strip()

    # Try to find About section
    about_candidates = soup.find_all(["p", "div"], string=lambda t: t and "about" in t.lower())
    if about_candidates:
        about_text = about_candidates[0].get_text(strip=True)

    favicon = soup.find("link", rel="icon")
    favicon_url = urljoin(url, favicon["href"]) if favicon and favicon.get("href") else ""

    return {
        "url": url,
        "company_name": title,
        "company_description": description,
        "company_information": about_text or description,
        "favicon": favicon_url,
        "keywords": keywords
    }
