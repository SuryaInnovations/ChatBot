"""
Workspace Package: File management, diff patching, sandboxed test running, versions, and project templates.
"""

from workspace.file_manager import default_file_manager, WorkspaceFileManager
from workspace.patch_manager import default_patch_manager, PatchManager
from workspace.test_runner import run_code_tests
from workspace.versions import default_version_manager, VersionHistoryManager, VersionSnapshot
from workspace.project_templates import TEMPLATES, get_template

__all__ = [
    "default_file_manager",
    "WorkspaceFileManager",
    "default_patch_manager",
    "PatchManager",
    "run_code_tests",
    "default_version_manager",
    "VersionHistoryManager",
    "VersionSnapshot",
    "TEMPLATES",
    "get_template"
]
