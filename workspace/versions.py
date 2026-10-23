"""
workspace/versions.py — File & Artifact Version History & Recovery.

Implements:
- Tracking version snapshots of files modified by the chatbot.
- Retrieving and comparing previous versions.
- Rolling back or restoring earlier snapshots.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class VersionSnapshot:
    version_id: int
    file_path: str
    content: str
    timestamp: float
    author: str = "assistant"
    commit_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VersionHistoryManager:
    def __init__(self):
        # file_path -> List[VersionSnapshot]
        self._history: Dict[str, List[VersionSnapshot]] = {}

    def save_snapshot(
        self,
        file_path: str,
        content: str,
        commit_message: str = "",
        author: str = "assistant"
    ) -> VersionSnapshot:
        """Records a new version snapshot for a file."""
        if file_path not in self._history:
            self._history[file_path] = []

        ver_id = len(self._history[file_path]) + 1
        snap = VersionSnapshot(
            version_id=ver_id,
            file_path=file_path,
            content=content,
            timestamp=time.time(),
            author=author,
            commit_message=commit_message or f"Version {ver_id}"
        )
        self._history[file_path].append(snap)
        return snap

    def get_versions(self, file_path: str) -> List[Dict[str, Any]]:
        snaps = self._history.get(file_path, [])
        return [s.to_dict() for s in snaps]

    def get_version(self, file_path: str, version_id: int) -> Optional[VersionSnapshot]:
        snaps = self._history.get(file_path, [])
        for s in snaps:
            if s.version_id == version_id:
                return s
        return None


default_version_manager = VersionHistoryManager()
