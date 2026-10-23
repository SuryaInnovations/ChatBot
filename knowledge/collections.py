"""
knowledge/collections.py — Knowledge Base Collections & Categorization.

Organizes documents into discrete workspaces/collections:
- "course_notes" (academic, study materials, lecture summaries)
- "project_docs" (specs, architectures, API schemas)
- "personal_files" (resumes, journals, personal notes)
- "research_library" (papers, reference articles)
"""

import time
import uuid
from typing import Dict, Any, List, Optional


class KnowledgeCollection:
    def __init__(
        self,
        collection_id: str,
        name: str,
        user_id: str,
        description: str = "",
        category: str = "general"
    ):
        self.collection_id = collection_id
        self.name = name
        self.user_id = user_id
        self.description = description
        self.category = category  # "course_notes", "project_docs", "personal_files", "general"
        self.created_at = time.time()
        self.document_ids: List[str] = []

    def add_document(self, doc_id: str):
        if doc_id not in self.document_ids:
            self.document_ids.append(doc_id)

    def remove_document(self, doc_id: str):
        if doc_id in self.document_ids:
            self.document_ids.remove(doc_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collection_id": self.collection_id,
            "name": self.name,
            "user_id": self.user_id,
            "description": self.description,
            "category": self.category,
            "created_at": self.created_at,
            "document_count": len(self.document_ids),
            "document_ids": list(self.document_ids)
        }


class CollectionManager:
    def __init__(self):
        self._collections: Dict[str, KnowledgeCollection] = {}

    def create_collection(
        self,
        name: str,
        user_id: str,
        category: str = "general",
        description: str = ""
    ) -> KnowledgeCollection:
        cid = f"col_{uuid.uuid4().hex[:10]}"
        col = KnowledgeCollection(
            collection_id=cid,
            name=name,
            user_id=user_id,
            description=description,
            category=category
        )
        self._collections[cid] = col
        return col

    def get_user_collections(self, user_id: str) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._collections.values() if c.user_id == user_id]

    def get_collection(self, collection_id: str) -> Optional[KnowledgeCollection]:
        return self._collections.get(collection_id)

    def delete_collection(self, collection_id: str, user_id: str) -> bool:
        col = self._collections.get(collection_id)
        if col and col.user_id == user_id:
            del self._collections[collection_id]
            return True
        return False


default_collection_manager = CollectionManager()
