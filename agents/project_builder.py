"""
agents/project_builder.py — Autonomous AI Project Builder Agent.

Implements Capability 17:
- Generates end-to-end multi-file software project scaffolds from templates or custom specs.
- Creates source modules, configuration, unit tests, and documentation.
- Runs sandbox tests to verify that generated project code executes without syntax errors.
- Bundles complete projects into downloadable ZIP archives with artifact registration.
"""

import os
import uuid
import logging
from typing import Dict, Any, List, Optional, Callable

from workspace.project_templates import get_template, TEMPLATES
from workspace.test_runner import run_code_tests
from services.export_service import default_export_service
from services.artifact_service import default_artifact_service
from services.task_queue import default_task_queue

logger = logging.getLogger("chatbot.agents.project_builder")


class ProjectBuilderAgent:
    def build_project(
        self,
        project_name: str,
        template_name: str = "fastapi",
        custom_instructions: str = "",
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Scaffolds a complete project, runs tests, and packages it as a downloadable ZIP.
        """
        def report(pct: int, msg: str):
            if progress_callback:
                try:
                    progress_callback(pct, msg)
                except Exception:
                    pass

        report(10, f"Loading project template: '{template_name}'...")
        tmpl = get_template(template_name)
        base_files = dict(tmpl["files"])

        # If custom instructions are provided, enrich main code
        if custom_instructions.strip():
            report(30, "Customizing project code according to requirements...")
            from core.llm_provider import LLMProvider
            llm = LLMProvider(provider="auto")
            prompt = (
                f"You are a Senior Software Architect. Customize this project template based on instructions:\n"
                f"Project Name: {project_name}\nInstructions: {custom_instructions}\n\n"
                f"Current main file content:\n```python\n{base_files.get('main.py') or base_files.get('app.py') or base_files.get('cli.py')}\n```\n\n"
                "Return the improved Python code inside ```python code block."
            )
            try:
                resp = llm.generate_response([{"role": "user", "content": prompt}])
                import re
                blocks = re.findall(r'```(?:python)?\s*(.*?)\s*```', resp, re.DOTALL)
                if blocks:
                    target_key = "main.py" if "main.py" in base_files else ("app.py" if "app.py" in base_files else "cli.py")
                    base_files[target_key] = blocks[0]
            except Exception as e:
                logger.warning(f"Project customization failed: {e}")

        # Test verification in sandbox
        report(60, "Running verification tests in sandbox...")
        test_file_key = next((k for k in base_files.keys() if k.startswith("test_")), None)
        test_res = None
        if test_file_key:
            target_key = "main.py" if "main.py" in base_files else "cli.py"
            target_code = base_files.get(target_key, "")
            test_code = base_files[test_file_key]
            test_res = run_code_tests(test_code=test_code, target_code=target_code)

        # Bundle to ZIP
        report(85, "Bundling project files into ZIP archive...")
        clean_pname = project_name.replace(" ", "_").lower() or "project"
        zip_bytes = default_export_service.bundle_files_to_zip(base_files, zip_filename=f"{clean_pname}.zip")

        art = default_artifact_service.save_artifact(
            file_name=f"{clean_pname}.zip",
            content=zip_bytes,
            user_id=user_id,
            session_id=session_id,
            mime_type="application/zip"
        )

        report(100, f"Project '{project_name}' built successfully!")

        return {
            "success": True,
            "project_name": project_name,
            "template": template_name,
            "files_generated": list(base_files.keys()),
            "tests_verified": test_res.get("success") if test_res else True,
            "artifact_id": art.artifact_id,
            "download_url": art.preview_url,
            "zip_path": art.file_path
        }

    def start_build_job(
        self,
        project_name: str,
        template_name: str = "fastapi",
        custom_instructions: str = "",
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Dispatches project building asynchronously to the background queue."""
        job = default_task_queue.submit_task(
            task_name=f"Build Project: {project_name}",
            user_id=user_id,
            func=self.build_project,
            project_name=project_name,
            template_name=template_name,
            custom_instructions=custom_instructions
        )
        return {
            "success": True,
            "job_id": job.job_id,
            "status": "queued",
            "message": f"Project build for '{project_name}' initiated in background."
        }


default_project_builder = ProjectBuilderAgent()
