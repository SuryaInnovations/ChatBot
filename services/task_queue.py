"""
services/task_queue.py — Asynchronous Background Task Queue & Progress Center.

Implements the SPARK-AI Long-Job Architecture:
- Dispatches heavy jobs (deep research, AutoML training, project builds, browser crawls).
- Acknowledges within 1–2 seconds with a unique job ID.
- Tracks real-time status: "queued", "running", "completed", "failed", "cancelled".
- Supports progress percentages (0–100%), live progress messages, and cancellation.
- Stores downloadable generated artifacts upon completion.
"""

import time
import uuid
import logging
import concurrent.futures
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("chatbot.services.task_queue")


@dataclass
class BackgroundJob:
    job_id: str
    task_name: str
    user_id: str
    status: str = "queued"  # "queued", "running", "completed", "failed", "cancelled"
    progress: int = 0  # 0 to 100
    status_message: str = "Job submitted"
    result: Optional[Any] = None
    error: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    cancelled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BackgroundTaskQueue:
    def __init__(self, max_workers: int = 4):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, BackgroundJob] = {}
        self._futures: Dict[str, concurrent.futures.Future] = {}

    def submit_task(
        self,
        task_name: str,
        user_id: str,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> BackgroundJob:
        """
        Submits a long task to the queue and returns immediately with a job ID.
        """
        jid = f"job_{uuid.uuid4().hex[:12]}"
        job = BackgroundJob(
            job_id=jid,
            task_name=task_name,
            user_id=user_id,
            status="queued"
        )
        self._jobs[jid] = job

        def runner():
            job.status = "running"
            job.started_at = time.time()
            job.progress = 5
            job.status_message = "Starting execution..."

            def update_progress(pct: int, msg: str = ""):
                if not job.cancelled:
                    job.progress = min(99, max(0, pct))
                    if msg:
                        job.status_message = msg

            try:
                # Inject progress reporter if accepted
                kwargs["progress_callback"] = update_progress
                res = func(*args, **kwargs)

                if job.cancelled:
                    job.status = "cancelled"
                    job.status_message = "Job was cancelled by user."
                    return

                job.status = "completed"
                job.progress = 100
                job.completed_at = time.time()
                job.status_message = "Execution completed successfully."
                job.result = res
                if isinstance(res, dict) and "artifacts" in res:
                    job.artifacts = res["artifacts"]

            except TypeError:
                # If function does not accept progress_callback, run without it
                kwargs.pop("progress_callback", None)
                try:
                    res = func(*args, **kwargs)
                    if job.cancelled:
                        job.status = "cancelled"
                        return
                    job.status = "completed"
                    job.progress = 100
                    job.completed_at = time.time()
                    job.result = res
                except Exception as ex:
                    job.status = "failed"
                    job.error = str(ex)
                    job.completed_at = time.time()
                    logger.error(f"Task {jid} failed: {ex}")

            except Exception as e:
                job.status = "failed"
                job.error = str(e)
                job.completed_at = time.time()
                logger.error(f"Task {jid} failed: {e}")

        future = self._executor.submit(runner)
        self._futures[jid] = future
        logger.info(f"[TASK QUEUE] Submitted job {jid} ('{task_name}') for user '{user_id}'")
        return job

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancels a queued or running job."""
        job = self._jobs.get(job_id)
        if not job:
            return False
        job.cancelled = True
        job.status = "cancelled"
        job.status_message = "Cancelled by user"
        future = self._futures.get(job_id)
        if future:
            future.cancel()
        return True

    def list_user_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        return [j.to_dict() for j in self._jobs.values() if j.user_id == user_id]


default_task_queue = BackgroundTaskQueue()
