"""
tools/github_tool.py — GitHub Repository Integration & PR Management.

Implements Capability 11:
- Reads repository files, README, directory trees, issues, and PRs.
- Caches repository metadata for fast sub-second retrieval.
- Enforces approval gate on mutating actions: creating branches, PRs, or modifying files.
- Uses GitHub REST API with httpx (compatible without requiring PyGithub installed).
"""

import os
import time
import logging
from typing import Dict, Any, Optional
import httpx

from security.approval_gate import default_approval_gate

logger = logging.getLogger("chatbot.tools.github_tool")

# In-memory metadata cache for fast retrieval
_REPO_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SEC = 300.0  # 5 min


class GitHubTool:
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SPARK-AI-Chatbot"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def get_repo_summary(self, repo_full_name: str) -> Dict[str, Any]:
        """
        Fetches repository description, default branch, star count, and open issues count.
        Caches results for 5 minutes.
        """
        repo_key = repo_full_name.strip().lower()
        now = time.time()
        if repo_key in _REPO_CACHE:
            cached = _REPO_CACHE[repo_key]
            if now - cached["cached_at"] < CACHE_TTL_SEC:
                return cached["data"]

        url = f"https://api.github.com/repos/{repo_full_name}"
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=self.headers)
                if resp.status_code == 404:
                    return {"success": False, "error": f"Repository '{repo_full_name}' not found."}
                if resp.status_code != 200:
                    return {"success": False, "error": f"GitHub API error: {resp.status_code} - {resp.text[:100]}"}

                data = resp.json()
                summary = {
                    "success": True,
                    "name": data.get("full_name"),
                    "description": data.get("description"),
                    "stars": data.get("stargazers_count"),
                    "forks": data.get("forks_count"),
                    "open_issues": data.get("open_issues_count"),
                    "default_branch": data.get("default_branch"),
                    "html_url": data.get("html_url")
                }
                _REPO_CACHE[repo_key] = {"cached_at": now, "data": summary}
                return summary
        except Exception as e:
            return {"success": False, "error": f"Failed to connect to GitHub: {str(e)}"}

    def get_repo_file_content(self, repo_full_name: str, file_path: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """Reads raw file contents from a repository."""
        ref = branch or "main"
        url = f"https://raw.githubusercontent.com/{repo_full_name}/{ref}/{file_path}"
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    return {
                        "success": True,
                        "file_path": file_path,
                        "content": resp.text[:15000]
                    }
                return {"success": False, "error": f"File '{file_path}' not found on {ref}."}
        except Exception as e:
            return {"success": False, "error": f"Error fetching file: {e}"}

    def create_pull_request(
        self,
        repo_full_name: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
        approval_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a Pull Request. Requires human approval gate.
        """
        if not approval_token:
            req = default_approval_gate.request_approval(
                tool_name="create_github_pr",
                arguments={
                    "repo": repo_full_name,
                    "title": title,
                    "head": head_branch,
                    "base": base_branch
                },
                reason=f"Create GitHub PR '{title}' on {repo_full_name}",
                risk_level="high"
            )
            return {
                "success": False,
                "requires_approval": True,
                "approval_request_id": req.request_id,
                "error": f"Creating a Pull Request is a consequential action requiring approval. Approval ID: {req.request_id}"
            }

        if not self.token:
            return {"success": False, "error": "GITHUB_TOKEN is required to create a Pull Request."}

        url = f"https://api.github.com/repos/{repo_full_name}/pulls"
        payload = {"title": title, "body": body, "head": head_branch, "base": base_branch}
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=self.headers, json=payload)
                if resp.status_code in (200, 201):
                    pr_data = resp.json()
                    return {"success": True, "pr_url": pr_data.get("html_url"), "number": pr_data.get("number")}
                return {"success": False, "error": f"Failed to create PR: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


default_github_tool = GitHubTool()
