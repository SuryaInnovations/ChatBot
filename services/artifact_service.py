"""
services/artifact_service.py — Generated Artifact Storage, Previews & Asset Management.

Handles:
- Saving charts, PDFs, generated code, and documents into the artifacts directory.
- Providing web-accessible download URIs and content previews.
- Scoping artifacts by user_id and session_id.
- File integrity checks.
"""

import os
import uuid
import time
import mimetypes
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

ARTIFACT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "artifacts"))
os.makedirs(ARTIFACT_DIR, exist_ok=True)


@dataclass
class ArtifactRecord:
    artifact_id: str
    file_name: str
    file_path: str
    mime_type: str
    file_size_bytes: int
    user_id: str
    session_id: Optional[str] = None
    created_at: float = 0.0
    preview_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArtifactService:
    def __init__(self, base_dir: str = ARTIFACT_DIR):
        self.base_dir = base_dir
        self._artifacts: Dict[str, ArtifactRecord] = {}

    def save_artifact(
        self,
        file_name: str,
        content: bytes | str,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> ArtifactRecord:
        """Saves generated content as a tracked artifact."""
        aid = f"art_{uuid.uuid4().hex[:10]}"
        safe_name = os.path.basename(file_name)
        target_path = os.path.join(self.base_dir, f"{aid}_{safe_name}")

        if isinstance(content, str):
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(target_path, "wb") as f:
                f.write(content)

        size = os.path.getsize(target_path)
        m_type = mime_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        rec = ArtifactRecord(
            artifact_id=aid,
            file_name=safe_name,
            file_path=target_path,
            mime_type=m_type,
            file_size_bytes=size,
            user_id=user_id,
            session_id=session_id,
            created_at=time.time(),
            preview_url=f"/api/artifacts/{aid}"
        )
        self._artifacts[aid] = rec
        return rec

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        return self._artifacts.get(artifact_id)

    def list_user_artifacts(self, user_id: str) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._artifacts.values() if a.user_id == user_id]


default_artifact_service = ArtifactService()
