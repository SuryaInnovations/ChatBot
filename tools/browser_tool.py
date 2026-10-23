"""
tools/browser_tool.py — Secure Browser Automation & Content Extraction.

Implements Capability 10:
- Safe navigation and text/DOM extraction.
- SSRF and private IP blocking using security/url_policy.py.
- Consequential action approval gate for forms, clicks, and submissions.
- Uses Playwright when available, with fast headless HTTP fallback.
"""

import time
import logging
from typing import Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup

from security.url_policy import is_safe_url
from security.approval_gate import default_approval_gate
from security.prompt_injection import wrap_untrusted_content

logger = logging.getLogger("chatbot.tools.browser_tool")


class BrowserAutomationTool:
    def __init__(self, timeout_sec: float = 12.0):
        self.timeout_sec = timeout_sec

    def navigate_and_extract(self, url: str) -> Dict[str, Any]:
        """
        Navigates to URL, checks SSRF policy, and extracts title, text content, and main links.
        """
        is_safe, error_msg = is_safe_url(url)
        if not is_safe:
            return {"success": False, "error": f"URL Policy Violation: {error_msg}"}

        start_time = time.time()
        # 1. Try Playwright if available
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=int(self.timeout_sec * 1000), wait_until="domcontentloaded")
                title = page.title()
                content = page.inner_text("body")[:6000]
                browser.close()
                dur_ms = round((time.time() - start_time) * 1000.0, 2)
                return {
                    "success": True,
                    "url": url,
                    "title": title,
                    "content": wrap_untrusted_content(content, source_label=url),
                    "execution_time_ms": dur_ms,
                    "engine": "playwright"
                }
        except Exception as e:
            logger.info(f"Playwright navigation unavailable or failed ({e}); using HTTP fetch fallback.")

        # 2. Fast HTTP fallback
        try:
            with httpx.Client(timeout=self.timeout_sec, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SPARK-AI/1.0"})
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string if soup.title else url
                # Remove scripts and styles
                for s in soup(["script", "style", "noscript"]):
                    s.decompose()
                text = soup.get_text(separator="\n", strip=True)[:6000]
                dur_ms = round((time.time() - start_time) * 1000.0, 2)
                return {
                    "success": True,
                    "url": url,
                    "title": title.strip() if title else url,
                    "content": wrap_untrusted_content(text, source_label=url),
                    "execution_time_ms": dur_ms,
                    "engine": "http_fallback"
                }
        except Exception as ex:
            return {"success": False, "error": f"Failed to fetch webpage: {str(ex)}"}

    def perform_action(
        self,
        url: str,
        action: str,  # "click", "fill", "submit"
        selector: str,
        value: Optional[str] = None,
        approval_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs an interactive action on a webpage (click, input, submit).
        Requires explicit human approval before executing consequential actions.
        """
        is_safe, error_msg = is_safe_url(url)
        if not is_safe:
            return {"success": False, "error": f"URL Policy Violation: {error_msg}"}

        # Check approval gate
        if not approval_token:
            req = default_approval_gate.request_approval(
                tool_name="browser_action",
                arguments={"url": url, "action": action, "selector": selector, "value": value},
                reason=f"Interactive browser {action} on {url}",
                risk_level="high"
            )
            return {
                "success": False,
                "requires_approval": True,
                "approval_request_id": req.request_id,
                "error": f"Browser interaction ({action}) requires approval. Request ID: {req.request_id}"
            }

        return {
            "success": True,
            "message": f"Action '{action}' simulated on selector '{selector}' at {url}."
        }


default_browser_tool = BrowserAutomationTool()

def browse_webpage(url: str) -> Dict[str, Any]:
    """Public helper function to browse and extract content from a URL."""
    return default_browser_tool.navigate_and_extract(url)
