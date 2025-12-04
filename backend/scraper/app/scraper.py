import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def normalize_url(url: str) -> str:
    # ef notandinn skrifar bara "visir.is" þá bætum við https:// fyrir framan
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    return url

def find_about_page(base_url, soup):
    candidates = []
    keywords = ["um", "about", "fyrirtaeki", "company", "info"]

    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        text = (a.get_text() or "").lower()

        if any(k in href for k in keywords) or any(k in text for k in keywords):
            candidates.append(urljoin(base_url, a["href"]))

    return candidates[0] if candidates else base_url


def extract_clean_text(soup):
    # fjarlægjum script/style o.fl.
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.extract()

    text = soup.get_text(separator=" ", strip=True)
    cleaned = " ".join(text.split())
    return cleaned

def get_internal_links(url, soup):
    base = url.split("//")[1].split("/")[0]
    links = []

    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        if base in href:
            links.append(href)

    return list(set(links))

def chunk_text(text, max_length=800):
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_length):
        chunk = " ".join(words[i:i+max_length])
        if len(chunk) > 50:  # tryggjum að chunk sé ekki of stuttur
            chunks.append(chunk)

    return chunks

def scrape_company_http(request):
    data = request.get_json()
    url = data.get("url")
    return scrape_company(url)

def scrape_company(url: str):
    url = normalize_url(url)

    # 1. Fetch HTML
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Failed to fetch URL: {str(e)}"}

    soup = BeautifulSoup(response.text, "html.parser")

    # 2. Basic metadata
    title = soup.title.string.strip() if soup.title else ""

    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""

    kw_tag = soup.find("meta", attrs={"name": "keywords"})
    keywords = kw_tag["content"].strip() if kw_tag and kw_tag.get("content") else ""

    favicon = soup.find("link", rel="icon")
    favicon_url = urljoin(url, favicon["href"]) if favicon and favicon.get("href") else ""

    # 3. Extract ABOUT PAGE TEXT
    try:
        about_url = find_about_page(url, soup)
        about_response = requests.get(about_url, timeout=10)
        about_response.raise_for_status()

        about_soup = BeautifulSoup(about_response.text, "html.parser")
        clean_text = extract_clean_text(about_soup)
        chunks = chunk_text(clean_text)

    except Exception:
        clean_text = ""
        chunks = []

    # 4. FALLBACK → You place THIS here
    if not clean_text or len(clean_text) < 50:
        clean_text = description if description else title
        chunks = [clean_text]

    # 5. Return final result
    return {
        "url": url,
        "company_name": title,
        "company_description": description,
        "keywords": keywords,
        "favicon": favicon_url,
        "clean_text": clean_text,
        "text_chunks": chunks
    }

