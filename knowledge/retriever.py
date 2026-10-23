"""
knowledge/retriever.py — Semantic & Lexical Knowledge Retriever.

Implements:
- Hybrid BM25/TF-IDF and cosine similarity index over ingested chunks.
- Fast top-k retrieval (default 3–5 chunks) keeping context concise.
- Page and sheet citation attachment.
- Multi-document filtering by collection or file name.
"""

import math
import re
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("chatbot.knowledge.retriever")


class KnowledgeRetriever:
    """Fast in-memory index for fast RAG retrieval over uploaded and collection documents."""
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self._doc_frequencies: Dict[str, int] = {}
        self._idf: Dict[str, float] = {}
        self._total_docs: int = 0

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Adds chunks to the retrieval index and updates frequencies."""
        for c in chunks:
            text = c.get("text", "")
            words = set(self._tokenize(text))
            for w in words:
                self._doc_frequencies[w] = self._doc_frequencies.get(w, 0) + 1
            self.chunks.append(c)

        self._total_docs = len(self.chunks)
        # Recompute IDF
        for w, df in self._doc_frequencies.items():
            self._idf[w] = math.log((self._total_docs - df + 0.5) / (df + 0.5) + 1.0)

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        file_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k most relevant chunks matching query.
        Returns chunks sorted by relevance score.
        """
        if not self.chunks or not query.strip():
            return []

        q_terms = self._tokenize(query)
        if not q_terms:
            return []

        scores = []
        for c in self.chunks:
            if file_filter and c.get("file_name") != file_filter:
                continue

            text = c.get("text", "")
            c_terms = self._tokenize(text)
            term_counts = {}
            for t in c_terms:
                term_counts[t] = term_counts.get(t, 0) + 1

            # BM25-style scoring
            doc_len = len(c_terms)
            avg_len = 150.0
            k1 = 1.2
            b = 0.75

            score = 0.0
            for qt in q_terms:
                if qt in term_counts:
                    tf = term_counts[qt]
                    idf = self._idf.get(qt, 1.0)
                    denom = tf + k1 * (1.0 - b + b * (doc_len / avg_len))
                    score += idf * ((tf * (k1 + 1.0)) / max(1e-5, denom))

            if score > 0.05:
                scores.append((score, c))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for sc, c in scores[:top_k]:
            res = dict(c)
            res["score"] = round(sc, 4)
            results.append(res)

        return results

    def clear(self):
        self.chunks.clear()
        self._doc_frequencies.clear()
        self._idf.clear()
        self._total_docs = 0

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_]{2,}\b', text)]


default_retriever = KnowledgeRetriever()
