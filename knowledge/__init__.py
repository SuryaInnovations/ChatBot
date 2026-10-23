"""
Knowledge Package: Ingestion, parsing, semantic retrieval, citations, and collections.
"""

from knowledge.citations import CitationManager, CitationSource, deduplicate_and_cite_web_results
from knowledge.ingest import default_ingest_pipeline, DocumentIngestionPipeline, chunk_text, compute_file_hash
from knowledge.retriever import default_retriever, KnowledgeRetriever
from knowledge.collections import default_collection_manager, CollectionManager, KnowledgeCollection

__all__ = [
    "CitationManager",
    "CitationSource",
    "deduplicate_and_cite_web_results",
    "default_ingest_pipeline",
    "DocumentIngestionPipeline",
    "chunk_text",
    "compute_file_hash",
    "default_retriever",
    "KnowledgeRetriever",
    "default_collection_manager",
    "CollectionManager",
    "KnowledgeCollection"
]
