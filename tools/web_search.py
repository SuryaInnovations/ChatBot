"""
Web search and URL content extraction tool.
"""

from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup

def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the live web for current information, documentation, news, or factual verification.
    """
    results = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for r in raw_results:
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", "") or r.get("link", ""),
                    "body": r.get("body", "") or r.get("snippet", "")
                })
    except Exception as e:
        # Fallback or error note
        results.append({
            "title": f"Search error: {str(e)}",
            "href": "",
            "body": "Unable to complete search via standard engine."
        })
    return results

def fetch_webpage_content(url: str, max_chars: int = 4000) -> str:
    """
    Fetches the textual content of a webpage given a URL.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=10.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove scripts and styles
            for elem in soup(["script", "style", "nav", "footer", "header"]):
                elem.extract()
            text = soup.get_text(separator="\n", strip=True)
            return text[:max_chars]
    except Exception as e:
        return f"Error fetching webpage {url}: {str(e)}"
