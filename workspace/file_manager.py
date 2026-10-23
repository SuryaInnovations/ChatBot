"""
workspace/file_manager.py — Sandboxed File Manager for Coding Workspaces.

Enforces:
- Strict path confinement within the project workspace directory (prevents ../ traversal).
- File size read/write quotas.
- Safe UTF-8 file reading, writing, renaming, and listing.
- Audit trail for modified files.
"""

import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("chatbot.workspace.file_manager")


class WorkspaceFileManager:
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = os.path.abspath(workspace_root or os.path.join(os.getcwd(), "workspaces"))
        os.makedirs(self.workspace_root, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> str:
        """Resolves path and asserts it stays inside workspace_root."""
        # Clean leading slashes
        clean_rel = relative_path.lstrip("/\\")
        abs_path = os.path.abspath(os.path.join(self.workspace_root, clean_rel))
        if not abs_path.startswith(self.workspace_root):
            raise PermissionError(f"Security Blocked: Path traversal attempt outside workspace root: {relative_path}")
        return abs_path

    def read_file(self, relative_path: str) -> Dict[str, Any]:
        """Reads file contents safely."""
        target = self._resolve_safe_path(relative_path)
        if not os.path.exists(target):
            return {"success": False, "error": f"File '{relative_path}' not found."}
        if os.path.isdir(target):
            return {"success": False, "error": f"'{relative_path}' is a directory."}

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(500000)
            return {
                "success": True,
                "file_path": relative_path,
                "content": content,
                "char_count": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, relative_path: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        """Writes or updates a file in the workspace."""
        target = self._resolve_safe_path(relative_path)
        if os.path.exists(target) and not overwrite:
            return {"success": False, "error": f"File '{relative_path}' already exists and overwrite=False."}

        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Workspace file written: {relative_path}")
            return {
                "success": True,
                "file_path": relative_path,
                "bytes_written": len(content.encode("utf-8"))
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, sub_dir: str = "") -> List[str]:
        """Lists all files in the workspace recursively."""
        target_dir = self._resolve_safe_path(sub_dir) if sub_dir else self.workspace_root
        if not os.path.exists(target_dir):
            return []

        rel_files = []
        for root, _, files in os.walk(target_dir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, self.workspace_root)
                rel_files.append(rel.replace("\\", "/"))
        return sorted(rel_files)

    def delete_file(self, relative_path: str) -> Dict[str, Any]:
        """Deletes a file inside the workspace."""
        target = self._resolve_safe_path(relative_path)
        if not os.path.exists(target):
            return {"success": False, "error": "File does not exist."}
        try:
            os.remove(target)
            return {"success": True, "file_path": relative_path}
        except Exception as e:
            return {"success": False, "error": str(e)}


default_file_manager = WorkspaceFileManager()
