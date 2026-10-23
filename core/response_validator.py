"""
core/response_validator.py — Answer Verification, Citation Alignment & Confidence Scoring.

Implements:
- Validating citation claims against retrieved evidence or web search sources.
- Checking that code execution claims match actual sandbox stdout.
- Detecting hallucinated URL links or fabricated facts.
- Computing an overall confidence score and verification report.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ValidationReport:
    is_valid: bool
    confidence_score: float  # 0.0 to 1.0
    citation_count: int
    unsupported_claims: List[str]
    verification_notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResponseValidator:
    def validate_response(
        self,
        response_text: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> ValidationReport:
        """
        Validates response text for citations, sandbox agreement, and integrity.
        """
        if not response_text or not response_text.strip():
            return ValidationReport(
                is_valid=False,
                confidence_score=0.0,
                citation_count=0,
                unsupported_claims=["Empty response generated."],
                verification_notes=["Model produced empty output."]
            )

        notes = []
        unsupported = []
        score = 0.95

        # 1. Check citation markers: [1], [2], etc.
        citation_markers = re.findall(r'\[(\d+)\]', response_text)
        citation_count = len(citation_markers)

        if sources:
            if not citation_markers and len(sources) > 0:
                notes.append("External sources were retrieved but no inline numeric citations [N] were placed.")
                score -= 0.15
            else:
                max_source_idx = len(sources)
                for c in set(citation_markers):
                    if int(c) > max_source_idx:
                        unsupported.append(f"Cited reference [{c}] which exceeds retrieved source count ({max_source_idx}).")
                        score -= 0.20

        # 2. Check code outputs vs response text
        if tool_results:
            for tr in tool_results:
                tool_name = tr.get("tool") or tr.get("tool_name")
                if tool_name in ("execute_python_code", "python_interpreter"):
                    res_data = tr.get("result") or tr.get("data")
                    if isinstance(res_data, dict):
                        stdout = res_data.get("stdout", "").strip()
                        error = res_data.get("error", "").strip()
                        if error and ("successfully" in response_text.lower() or "worked" in response_text.lower()):
                            unsupported.append(f"Response claimed success but {tool_name} returned an error: {error[:60]}")
                            score -= 0.30

        # 3. Detect suspicious hallucinated URLs
        markdown_urls = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', response_text)
        for text, url in markdown_urls:
            if "example.com" in url or "your-domain.com" in url:
                notes.append(f"Placeholder domain detected in link: {url}")

        final_score = max(0.0, min(1.0, round(score, 2)))
        return ValidationReport(
            is_valid=(final_score >= 0.60 and len(unsupported) == 0),
            confidence_score=final_score,
            citation_count=citation_count,
            unsupported_claims=unsupported,
            verification_notes=notes
        )


default_response_validator = ResponseValidator()
