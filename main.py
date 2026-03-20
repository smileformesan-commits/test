"""
GitHub Workflow Steps API
Wraps the GitHub REST API to expose workflow run step details.
"""

import os
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(
    title="GitHub Workflow Steps API",
    description=(
        "A REST API that wraps the GitHub Actions REST API to fetch "
        "workflow run details including job steps."
    ),
    version="1.0.0",
)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"


def _github_headers(token: Optional[str]) -> dict:
    """Build GitHub API request headers."""
    resolved_token = token or os.getenv("GITHUB_TOKEN")
    if not resolved_token:
        raise HTTPException(
            status_code=401,
            detail=(
                "GitHub token is required. Pass it via the "
                "X-GitHub-Token header or set the GITHUB_TOKEN environment variable."
            ),
        )
    return {
        "Authorization": f"Bearer {resolved_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


async def _github_get(url: str, headers: dict, params: dict = None) -> dict:
    """Perform an authenticated GET request against the GitHub API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params or {})
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired GitHub token.")
    if response.status_code == 403:
        raise HTTPException(status_code=403, detail="GitHub API rate limit exceeded or insufficient permissions.")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Resource not found on GitHub.")
    if not response.is_success:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"GitHub API error: {response.text}",
        )
    return response.json()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/repos/{owner}/{repo}/workflows",
    summary="List workflows",
    tags=["Workflows"],
    response_description="Paginated list of workflows in the repository",
)
async def list_workflows(
    owner: str,
    repo: str,
    per_page: int = Query(30, ge=1, le=100, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number"),
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    List all workflows defined in a repository.

    **GitHub API:** `GET /repos/{owner}/{repo}/actions/workflows`
    """
    headers = _github_headers(x_github_token)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/workflows"
    data = await _github_get(url, headers, {"per_page": per_page, "page": page})
    return data


@app.get(
    "/api/repos/{owner}/{repo}/workflows/{workflow_id}/runs",
    summary="List runs for a specific workflow",
    tags=["Workflow Runs"],
    response_description="Paginated list of runs for the given workflow",
)
async def list_workflow_runs(
    owner: str,
    repo: str,
    workflow_id: str,
    branch: Optional[str] = Query(None, description="Filter by branch name"),
    status: Optional[str] = Query(
        None,
        description=(
            "Filter by status: queued, in_progress, completed, "
            "waiting, requested, pending, action_required, cancelled, "
            "failure, neutral, skipped, stale, success, timed_out"
        ),
    ),
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    List runs for a specific workflow (by workflow file name or numeric ID).

    **GitHub API:** `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs`
    """
    headers = _github_headers(x_github_token)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
    params = {"per_page": per_page, "page": page}
    if branch:
        params["branch"] = branch
    if status:
        params["status"] = status
    data = await _github_get(url, headers, params)
    return data


@app.get(
    "/api/repos/{owner}/{repo}/runs",
    summary="List all workflow runs for a repository",
    tags=["Workflow Runs"],
    response_description="Paginated list of all workflow runs in the repository",
)
async def list_repo_workflow_runs(
    owner: str,
    repo: str,
    branch: Optional[str] = Query(None, description="Filter by branch name"),
    status: Optional[str] = Query(None, description="Filter by run status"),
    event: Optional[str] = Query(None, description="Filter by triggering event (push, pull_request, etc.)"),
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    List all workflow runs across all workflows in a repository.

    **GitHub API:** `GET /repos/{owner}/{repo}/actions/runs`
    """
    headers = _github_headers(x_github_token)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs"
    params = {"per_page": per_page, "page": page}
    if branch:
        params["branch"] = branch
    if status:
        params["status"] = status
    if event:
        params["event"] = event
    data = await _github_get(url, headers, params)
    return data


@app.get(
    "/api/repos/{owner}/{repo}/runs/{run_id}",
    summary="Get a single workflow run",
    tags=["Workflow Runs"],
    response_description="Full details of a workflow run",
)
async def get_workflow_run(
    owner: str,
    repo: str,
    run_id: int,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    Get full details of a single workflow run by its numeric run ID.

    **GitHub API:** `GET /repos/{owner}/{repo}/actions/runs/{run_id}`
    """
    headers = _github_headers(x_github_token)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs/{run_id}"
    return await _github_get(url, headers)


@app.get(
    "/api/repos/{owner}/{repo}/runs/{run_id}/jobs",
    summary="List jobs for a workflow run",
    tags=["Jobs & Steps"],
    response_description="Paginated list of jobs (each containing their steps)",
)
async def list_run_jobs(
    owner: str,
    repo: str,
    run_id: int,
    filter: Optional[str] = Query(
        "latest",
        description="Filter jobs: 'latest' (default) returns jobs from the most recent run attempt; 'all' returns every attempt",
    ),
    per_page: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1),
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    List all jobs for a workflow run.  Each job object contains a `steps` array
    with the status and timing of every step executed in that job.

    **GitHub API:** `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs`
    """
    headers = _github_headers(x_github_token)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
    params = {"filter": filter, "per_page": per_page, "page": page}
    return await _github_get(url, headers, params)


@app.get(
    "/api/repos/{owner}/{repo}/jobs/{job_id}",
    summary="Get a single job (with steps)",
    tags=["Jobs & Steps"],
    response_description="Job details including the full steps array",
)
async def get_job(
    owner: str,
    repo: str,
    job_id: int,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    Get a single job by its numeric job ID.  The response includes the `steps`
    array with each step's `name`, `status`, `conclusion`, `started_at`,
    and `completed_at`.

    **GitHub API:** `GET /repos/{owner}/{repo}/actions/jobs/{job_id}`
    """
    headers = _github_headers(x_github_token)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/jobs/{job_id}"
    return await _github_get(url, headers)


@app.get(
    "/api/repos/{owner}/{repo}/jobs/{job_id}/steps",
    summary="Get steps for a single job",
    tags=["Jobs & Steps"],
    response_description="Array of step objects for the specified job",
)
async def get_job_steps(
    owner: str,
    repo: str,
    job_id: int,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    Convenience endpoint: fetches the job and returns **only the `steps` array**.

    Each step contains:
    - `number` – step index (1-based)
    - `name` – step display name
    - `status` – `queued` | `in_progress` | `completed`
    - `conclusion` – `success` | `failure` | `skipped` | `cancelled` | `timed_out` | `null`
    - `started_at` – ISO-8601 datetime (or `null`)
    - `completed_at` – ISO-8601 datetime (or `null`)

    **GitHub API (underlying):** `GET /repos/{owner}/{repo}/actions/jobs/{job_id}`
    """
    headers = _github_headers(x_github_token)
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/jobs/{job_id}"
    data = await _github_get(url, headers)
    steps = data.get("steps", [])
    return {"job_id": job_id, "job_name": data.get("name"), "total_steps": len(steps), "steps": steps}


@app.get(
    "/api/repos/{owner}/{repo}/runs/{run_id}/steps",
    summary="Get all steps across all jobs in a workflow run",
    tags=["Jobs & Steps"],
    response_description="Aggregated steps grouped by job for the entire workflow run",
)
async def get_run_steps(
    owner: str,
    repo: str,
    run_id: int,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    Aggregate view: fetches every job in the workflow run and returns all steps
    grouped by job.  This is the most convenient endpoint to get a full picture
    of every step executed in a run.

    **GitHub APIs used internally:**
    1. `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs`
    2. (steps are embedded in each job – no extra requests needed)
    """
    headers = _github_headers(x_github_token)
    jobs_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"

    # Paginate through all jobs
    all_jobs = []
    page = 1
    while True:
        data = await _github_get(jobs_url, headers, {"per_page": 100, "page": page})
        jobs = data.get("jobs", [])
        all_jobs.extend(jobs)
        if len(jobs) < 100:
            break
        page += 1

    result = []
    for job in all_jobs:
        result.append(
            {
                "job_id": job.get("id"),
                "job_name": job.get("name"),
                "status": job.get("status"),
                "conclusion": job.get("conclusion"),
                "started_at": job.get("started_at"),
                "completed_at": job.get("completed_at"),
                "runner_name": job.get("runner_name"),
                "total_steps": len(job.get("steps", [])),
                "steps": job.get("steps", []),
            }
        )

    return {
        "run_id": run_id,
        "total_jobs": len(result),
        "jobs": result,
    }


@app.get(
    "/api/repos/{owner}/{repo}/jobs/{job_id}/logs",
    summary="Get the log download URL for a job",
    tags=["Jobs & Steps"],
    response_description="A time-limited URL to download the plain-text log for a job",
)
async def get_job_log_url(
    owner: str,
    repo: str,
    job_id: int,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """
    Returns the redirect URL that points to the downloadable plain-text log for
    a job.  The URL expires after **1 minute**.

    **GitHub API:** `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs`

    Note: GitHub returns a `302 Found` with a `Location` header.  This endpoint
    captures and returns that URL rather than streaming the log content directly.
    """
    resolved_token = x_github_token or os.getenv("GITHUB_TOKEN")
    if not resolved_token:
        raise HTTPException(
            status_code=401,
            detail="GitHub token is required.",
        )
    headers = {
        "Authorization": f"Bearer {resolved_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
    async with httpx.AsyncClient(follow_redirects=False) as client:
        response = await client.get(url, headers=headers)

    if response.status_code == 302:
        log_url = response.headers.get("Location")
        return {"job_id": job_id, "log_url": log_url, "expires_in": "60 seconds"}
    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired GitHub token.")
    if response.status_code == 403:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Job not found.")
    raise HTTPException(status_code=response.status_code, detail=response.text)


@app.get("/health", tags=["Meta"], summary="Health check")
async def health():
    """Returns a simple health-check response."""
    return {"status": "ok", "github_api_version": GITHUB_API_VERSION}
