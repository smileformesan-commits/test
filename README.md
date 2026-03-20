# GitHub Workflow Steps API

A FastAPI service that wraps the [GitHub Actions REST API](https://docs.github.com/en/rest/actions) to expose workflow run step details through clean, well-documented endpoints.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your GitHub token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxx
# or copy .env.example → .env and fill in the value

# 3. Start the server
uvicorn main:app --reload
```

The interactive docs are available at **http://localhost:8000/docs** (Swagger UI) and **http://localhost:8000/redoc** (ReDoc).

---

## Authentication

Every endpoint requires a GitHub token. You can supply it in two ways:

| Method | How |
|---|---|
| Environment variable | `export GITHUB_TOKEN=<token>` |
| Per-request header | `X-GitHub-Token: <token>` |

The token needs the `repo` scope for private repositories or `public_repo` for public ones.

---

## API Reference

### Meta

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |

---

### Workflows

| Method | Path | Description |
|---|---|---|
| GET | `/api/repos/{owner}/{repo}/workflows` | List all workflows in a repo |

**Query params:** `per_page`, `page`

---

### Workflow Runs

| Method | Path | Description |
|---|---|---|
| GET | `/api/repos/{owner}/{repo}/runs` | List all workflow runs in a repo |
| GET | `/api/repos/{owner}/{repo}/runs/{run_id}` | Get a single workflow run |
| GET | `/api/repos/{owner}/{repo}/workflows/{workflow_id}/runs` | List runs for a specific workflow |

**Query params (list endpoints):** `branch`, `status`, `event`, `per_page`, `page`

**Status values:** `queued`, `in_progress`, `completed`, `waiting`, `requested`, `pending`, `action_required`, `cancelled`, `failure`, `neutral`, `skipped`, `stale`, `success`, `timed_out`

---

### Jobs & Steps

| Method | Path | Description |
|---|---|---|
| GET | `/api/repos/{owner}/{repo}/runs/{run_id}/jobs` | List all jobs for a run (each job contains its steps) |
| GET | `/api/repos/{owner}/{repo}/runs/{run_id}/steps` | **Aggregated view** – all steps grouped by job for an entire run |
| GET | `/api/repos/{owner}/{repo}/jobs/{job_id}` | Get a single job with its steps |
| GET | `/api/repos/{owner}/{repo}/jobs/{job_id}/steps` | Get **only** the steps array for a job |
| GET | `/api/repos/{owner}/{repo}/jobs/{job_id}/logs` | Get the time-limited log download URL for a job |

---

## Step Object Schema

Steps are returned as objects with the following fields:

```json
{
  "number": 1,
  "name": "Set up job",
  "status": "completed",
  "conclusion": "success",
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T10:00:05Z"
}
```

| Field | Type | Values |
|---|---|---|
| `number` | integer | Step index (1-based) |
| `name` | string | Step display name |
| `status` | string | `queued` \| `in_progress` \| `completed` |
| `conclusion` | string \| null | `success` \| `failure` \| `skipped` \| `cancelled` \| `timed_out` \| `neutral` \| `null` |
| `started_at` | datetime \| null | ISO-8601 |
| `completed_at` | datetime \| null | ISO-8601 |

---

## Example curl Requests

```bash
TOKEN=ghp_xxxxxxxxxxxxxxxxxx
OWNER=octocat
REPO=hello-world

# List all workflows
curl -H "X-GitHub-Token: $TOKEN" \
  http://localhost:8000/api/repos/$OWNER/$REPO/workflows

# List recent workflow runs
curl -H "X-GitHub-Token: $TOKEN" \
  "http://localhost:8000/api/repos/$OWNER/$REPO/runs?per_page=5"

# Get all jobs (with steps) for run 12345678
curl -H "X-GitHub-Token: $TOKEN" \
  http://localhost:8000/api/repos/$OWNER/$REPO/runs/12345678/jobs

# Get aggregated step view for the entire run
curl -H "X-GitHub-Token: $TOKEN" \
  http://localhost:8000/api/repos/$OWNER/$REPO/runs/12345678/steps

# Get steps for a specific job
curl -H "X-GitHub-Token: $TOKEN" \
  http://localhost:8000/api/repos/$OWNER/$REPO/jobs/987654321/steps

# Get the log download URL for a job
curl -H "X-GitHub-Token: $TOKEN" \
  http://localhost:8000/api/repos/$OWNER/$REPO/jobs/987654321/logs
```

---

## Underlying GitHub REST APIs

| This API endpoint | GitHub REST API called |
|---|---|
| `/api/repos/.../workflows` | `GET /repos/{owner}/{repo}/actions/workflows` |
| `/api/repos/.../workflows/{id}/runs` | `GET /repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs` |
| `/api/repos/.../runs` | `GET /repos/{owner}/{repo}/actions/runs` |
| `/api/repos/.../runs/{run_id}` | `GET /repos/{owner}/{repo}/actions/runs/{run_id}` |
| `/api/repos/.../runs/{run_id}/jobs` | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs` |
| `/api/repos/.../runs/{run_id}/steps` | `GET /repos/{owner}/{repo}/actions/runs/{run_id}/jobs` (paginated, aggregated) |
| `/api/repos/.../jobs/{job_id}` | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}` |
| `/api/repos/.../jobs/{job_id}/steps` | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}` (steps extracted) |
| `/api/repos/.../jobs/{job_id}/logs` | `GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs` |
