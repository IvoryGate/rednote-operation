"""Background workflow runner that shells out to existing CLI scripts."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class WorkflowSpec:
    name: str
    description: str
    build_cmd: Callable[[dict[str, Any]], list[str]]
    requires_browser: bool = False
    default_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Job:
    id: str
    workflow: str
    status: str  # pending | running | succeeded | failed
    params: dict[str, Any]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    requires_browser: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _py(*script_and_args: str) -> list[str]:
    return [sys.executable, *script_and_args]


def _build_analyze_performance(params: dict[str, Any]) -> list[str]:
    days = str(params.get("days", 30))
    top = str(params.get("top", 20))
    sort_by = str(params.get("sort_by", "likes"))
    out = Path(params.get("output") or "exports/workflow_performance.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = _py(
        "scripts/analyze/content_performance.py",
        "--from-db",
        "--days",
        days,
        "--top",
        top,
        "--sort-by",
        sort_by,
        "--output",
        str(out),
    )
    if params.get("viral_threshold") is not None:
        cmd.extend(["--viral-threshold", str(params["viral_threshold"])])
    if params.get("cost") is not None:
        cmd.extend(["--cost", str(params["cost"])])
    return cmd


def _build_analyze_keywords(params: dict[str, Any]) -> list[str]:
    top = str(params.get("top", 50))
    out = Path(params.get("output") or "exports/workflow_keywords.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = _py(
        "scripts/analyze/keyword_insights.py",
        "--from-db",
        "--top",
        top,
        "--output",
        str(out),
    )
    if params.get("update_db"):
        cmd.append("--update-db")
    return cmd


def _build_analyze_competitors(params: dict[str, Any]) -> list[str]:
    days = str(params.get("days", 30))
    out = Path(params.get("output") or "exports/workflow_competitors.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = _py(
        "scripts/analyze/competitor_report.py",
        "--compare",
        "--days",
        days,
        "--output",
        str(out),
    )
    for name in params.get("competitors") or []:
        cmd.extend(["--competitor", str(name)])
    return cmd


def _build_generate_brief(params: dict[str, Any]) -> list[str]:
    topic = str(params.get("topic") or "").strip()
    category = str(params.get("category") or "").strip()
    if not topic or not category:
        raise ValueError("topic and category are required")
    out = Path(params.get("output") or f"data/drafts/brief_{uuid.uuid4().hex[:8]}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = _py(
        "scripts/create/generate_post.py",
        "--topic",
        topic,
        "--category",
        category,
        "--output",
        str(out),
    )
    if params.get("template"):
        cmd.extend(["--template", str(params["template"])])
    if params.get("to_db"):
        cmd.append("--db")
    return cmd


def _build_finalize_post(params: dict[str, Any]) -> list[str]:
    brief = str(params.get("brief") or "").strip()
    if not brief:
        raise ValueError("brief path is required")
    out = Path(params.get("output") or "data/drafts/final_from_workflow.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = _py(
        "scripts/create/finalize_post.py",
        "--brief",
        brief,
        "--output",
        str(out),
    )
    if params.get("no_strict"):
        cmd.append("--no-strict")
    if params.get("require_images"):
        cmd.append("--require-images")
    for img in params.get("images") or []:
        cmd.extend(["--image", str(img)])
    if params.get("queue"):
        publish_time = params.get("time")
        if not publish_time:
            raise ValueError("time is required when queue=true")
        cmd.extend(["--queue", "--time", str(publish_time)])
    return cmd


def _build_publish_now(params: dict[str, Any]) -> list[str]:
    account = str(params.get("account") or "main")
    dry_run = params.get("dry_run", True)
    cmd = _py("scripts/publish/publish_now.py", "--account", account)
    if params.get("queue_id") is not None:
        cmd.extend(["--queue-id", str(params["queue_id"])])
    elif params.get("draft"):
        cmd.extend(["--draft", str(params["draft"])])
    else:
        raise ValueError("queue_id or draft is required")
    if dry_run:
        cmd.append("--dry-run")
    else:
        cmd.append("--no-dry-run")
    if params.get("headless", True):
        cmd.append("--headless")
    else:
        cmd.append("--no-headless")
    return cmd


def _build_crawl_search(params: dict[str, Any]) -> list[str]:
    keywords = params.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [keywords]
    if not keywords:
        raise ValueError("keywords is required")
    out = Path(params.get("output") or "exports/workflow_search.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = _py("scripts/crawl/search_trending.py", "--output", str(out), "--headless")
    for kw in keywords:
        cmd.extend(["--keyword", str(kw)])
    if params.get("count") is not None:
        cmd.extend(["--count", str(params["count"])])
    if params.get("account"):
        cmd.extend(["--account", str(params["account"])])
    return cmd


WORKFLOWS: dict[str, WorkflowSpec] = {
    "analyze.performance": WorkflowSpec(
        name="analyze.performance",
        description="Run content_performance.py against the DB",
        build_cmd=_build_analyze_performance,
    ),
    "analyze.keywords": WorkflowSpec(
        name="analyze.keywords",
        description="Run keyword_insights.py against the DB",
        build_cmd=_build_analyze_keywords,
    ),
    "analyze.competitors": WorkflowSpec(
        name="analyze.competitors",
        description="Run competitor_report.py (--compare or named competitors)",
        build_cmd=_build_analyze_competitors,
    ),
    "create.brief": WorkflowSpec(
        name="create.brief",
        description="Generate a post creation brief JSON",
        build_cmd=_build_generate_brief,
    ),
    "create.finalize": WorkflowSpec(
        name="create.finalize",
        description="Validate brief and emit publish-ready draft (optional queue)",
        build_cmd=_build_finalize_post,
    ),
    "publish.now": WorkflowSpec(
        name="publish.now",
        description="Publish or dry-run a draft / queue item via browser",
        build_cmd=_build_publish_now,
        requires_browser=True,
        default_params={"dry_run": True, "headless": True},
    ),
    "crawl.search": WorkflowSpec(
        name="crawl.search",
        description="Search trending notes for keywords (browser)",
        build_cmd=_build_crawl_search,
        requires_browser=True,
    ),
}


class WorkflowRunner:
    """In-memory job registry with threaded subprocess execution."""

    def __init__(self, *, timeout_seconds: int = 600) -> None:
        self.timeout_seconds = timeout_seconds
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def list_workflows(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "requires_browser": spec.requires_browser,
                "default_params": spec.default_params,
            }
            for spec in WORKFLOWS.values()
        ]

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> list[Job]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]

    def submit(
        self,
        workflow: str,
        params: dict[str, Any] | None = None,
        *,
        background: bool = True,
    ) -> Job:
        if workflow not in WORKFLOWS:
            raise KeyError(f"Unknown workflow: {workflow}")
        spec = WORKFLOWS[workflow]
        merged = {**spec.default_params, **(params or {})}
        # Validate command build early for clear API errors
        cmd = spec.build_cmd(merged)
        job = Job(
            id=uuid.uuid4().hex,
            workflow=workflow,
            status="pending",
            params=merged,
            created_at=datetime.now().isoformat(timespec="seconds"),
            requires_browser=spec.requires_browser,
        )
        with self._lock:
            self._jobs[job.id] = job

        if background:
            thread = threading.Thread(
                target=self._execute,
                args=(job.id, cmd),
                daemon=True,
                name=f"workflow-{job.id[:8]}",
            )
            thread.start()
        else:
            self._execute(job.id, cmd)
        return job

    def _execute(self, job_id: str, cmd: list[str]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = datetime.now().isoformat(timespec="seconds")

        try:
            completed = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            with self._lock:
                job = self._jobs[job_id]
                job.returncode = completed.returncode
                job.stdout = (completed.stdout or "")[-8000:]
                job.stderr = (completed.stderr or "")[-8000:]
                job.finished_at = datetime.now().isoformat(timespec="seconds")
                if completed.returncode == 0:
                    job.status = "succeeded"
                else:
                    job.status = "failed"
                    job.error = f"exit code {completed.returncode}"
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or ""
            err = exc.stderr or ""
            if isinstance(out, bytes):
                out = out.decode("utf-8", errors="replace")
            if isinstance(err, bytes):
                err = err.decode("utf-8", errors="replace")
            with self._lock:
                job = self._jobs[job_id]
                job.status = "failed"
                job.error = f"timeout after {self.timeout_seconds}s"
                job.stdout = str(out)[-8000:]
                job.stderr = str(err)[-8000:]
                job.finished_at = datetime.now().isoformat(timespec="seconds")
        except Exception as exc:
            with self._lock:
                job = self._jobs[job_id]
                job.status = "failed"
                job.error = str(exc)
                job.finished_at = datetime.now().isoformat(timespec="seconds")

        self._persist_log(job_id)

    def _persist_log(self, job_id: str) -> None:
        try:
            from src.core.db import SessionLocal, init_db
            from src.models import OperationLog

            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                payload = job.to_dict()

            init_db()
            db = SessionLocal()
            try:
                db.add(
                    OperationLog(
                        action=f"workflow.{job.workflow}",
                        entity_type="workflow_job",
                        entity_id=job.id,
                        details=json.dumps(payload, ensure_ascii=False)[:4000],
                        status="success" if job.status == "succeeded" else "failed",
                    )
                )
                db.commit()
            finally:
                db.close()
        except Exception:
            # Logging must not break workflow execution.
            return


# Process-wide runner used by the API.
runner = WorkflowRunner()
