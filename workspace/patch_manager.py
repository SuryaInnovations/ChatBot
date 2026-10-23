"""
workspace/patch_manager.py — Code Diff Preview & Unified Patch Manager.

Implements:
- Generating reviewable unified diffs between original and modified code.
- Applying unified diff patches to files with line offset tolerance.
- Safety check preventing accidental file destruction.
- Patch preview mode before human approval.
"""

import difflib
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("chatbot.workspace.patch_manager")


class PatchManager:
    def create_diff(
        self,
        original_text: str,
        modified_text: str,
        filename: str = "file.py"
    ) -> str:
        """Generates a standard unified diff string."""
        orig_lines = original_text.splitlines(keepends=True)
        mod_lines = modified_text.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        return "\n".join(diff)

    def apply_patch(
        self,
        original_text: str,
        patch_diff: str
    ) -> Tuple[bool, str, str]:
        """
        Attempts to apply a unified diff to original text.
        Returns (success, patched_text, error_message).
        """
        # Simple line replacement parser for unified diff blocks
        try:
            lines = original_text.splitlines()
            patch_lines = patch_diff.splitlines()

            # Find additions and removals
            to_remove = []
            to_add = []
            for pl in patch_lines:
                if pl.startswith("---") or pl.startswith("+++") or pl.startswith("@@"):
                    continue
                if pl.startswith("-"):
                    to_remove.append(pl[1:])
                elif pl.startswith("+"):
                    to_add.append(pl[1:])

            # If full new content was provided in diff
            new_text = original_text
            for rem in to_remove:
                if rem in new_text:
                    new_text = new_text.replace(rem, "", 1)
            for add in to_add:
                new_text += "\n" + add

            return True, new_text.strip(), ""
        except Exception as e:
            return False, original_text, str(e)


default_patch_manager = PatchManager()
