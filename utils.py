import time
import requests
from urllib.parse import quote_plus, urlencode, urlparse, parse_qs, urlunparse
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/107.0.0.0 Safari/537.36"
    )
}

def get_response(url: str, retries: int = 3, backoff: int = 5) -> requests.Response:
    """
    GET with retry on 429 rate limits.
    """
    for attempt in range(retries):
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 429:
            time.sleep(backoff * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()

# URL builders
def build_search_url(base: str, params: dict) -> str:
    """
    Construct URL with query params.
    """
    return f"{base}?{urlencode(params, doseq=True, quote_via=quote_plus)}"