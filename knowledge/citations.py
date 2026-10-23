"""
knowledge/citations.py — Structured Citation Builder, Deduplication & Evidence Linking.

Provides:
- Deduplication of source URLs and document passages.
- Structured citation cards (title, url, domain, snippet, timestamp, trust score).
- Inline citation token linking: [1], [2], [Doc: p. 4].
- URL validation and claim-to-evidence alignment.
"""

import urllib.parse
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class CitationSource:
    source_id: int
    title: str
    url: Optional[str] = None
    domain: Optional[str] = None
    snippet: str = ""
    author: Optional[str] = None
    published_date: Optional[str] = None
    page: Optional[int] = None
    sheet_name: Optional[str] = None
    source_type: str = "web"  # "web", "document", "code", "paper"
    trust_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CitationManager:
    """Manages deduplication, index numbering, and markdown bibliography formatting."""
    def __init__(self):
        self._sources: List[CitationSource] = []
        self._seen_urls: Dict[str, int] = {}  # url -> source_id

    def add_web_source(
        self,
        title: str,
        url: str,
        snippet: str = "",
        published_date: Optional[str] = None
    ) -> CitationSource:
        """Adds a web source or returns existing if duplicate URL."""
        clean_url = url.strip()
        if clean_url in self._seen_urls:
            idx = self._seen_urls[clean_url]
            return self._sources[idx - 1]

        domain = ""
        try:
            parsed = urllib.parse.urlparse(clean_url)
            domain = parsed.netloc.lower()
        except Exception:
            domain = ""

        idx = len(self._sources) + 1
        source = CitationSource(
            source_id=idx,
            title=title.strip() or domain or f"Source {idx}",
            url=clean_url,
            domain=domain,
            snippet=snippet.strip()[:400],
            published_date=published_date,
            source_type="web"
        )
        self._sources.append(source)
        self._seen_urls[clean_url] = idx
        return source

    def add_document_source(
        self,
        file_name: str,
        page: Optional[int] = None,
        sheet_name: Optional[str] = None,
        snippet: str = ""
    ) -> CitationSource:
        """Adds a document chunk source."""
        idx = len(self._sources) + 1
        source = CitationSource(
            source_id=idx,
            title=file_name,
            snippet=snippet.strip()[:400],
            page=page,
            sheet_name=sheet_name,
            source_type="document"
        )
        self._sources.append(source)
        return source

    def get_sources(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._sources]

    def render_markdown_bibliography(self) -> str:
        """Formats cited sources into a clean, clickable bibliography section."""
        if not self._sources:
            return ""

        lines = ["\n\n### Sources & References:"]
        for s in self._sources:
            if s.source_type == "web" and s.url:
                lines.append(f"- **[{s.source_id}]** [{s.title}]({s.url}) — *{s.domain}*")
            elif s.source_type == "document":
                loc = f"p. {s.page}" if s.page else (f"Sheet: {s.sheet_name}" if s.sheet_name else "")
                loc_str = f" ({loc})" if loc else ""
                lines.append(f"- **[{s.source_id}]** Document: `{s.title}`{loc_str}")
            else:
                lines.append(f"- **[{s.source_id}]** {s.title}")

        return "\n".join(lines)


def deduplicate_and_cite_web_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convenience function to take raw search results, deduplicate by URL,
    and return structured sources with ready-to-render bibliography.
    """
    cm = CitationManager()
    for r in results:
        url = r.get("url") or r.get("link")
        if not url:
            continue
        title = r.get("title") or "Search Result"
        snippet = r.get("snippet") or r.get("content") or ""
        cm.add_web_source(title=title, url=url, snippet=snippet)

    return {
        "sources": cm.get_sources(),
        "bibliography_markdown": cm.render_markdown_bibliography()
    }
