# FlowForge

FlowForge is an AI-powered workflow orchestration and execution platform. It demonstrates a production-style control plane for building DAG workflows, validating graph structure, running asynchronous node execution, inspecting logs, managing workflow versions, and monitoring workers.

It is a portfolio-grade reference implementation: lighter than Temporal or Airflow, more visual than GitHub Actions, and AI-aware without requiring paid APIs for the local demo.

## Architecture

```text
Browser -> Next.js UI -> FastAPI API -> PostgreSQL
                         |             |
                         |             -> Audit logs, versions, executions
                         -> Redis -> Celery workers -> Node runners
                         -> Prometheus metrics -> Grafana dashboards
Nginx reverse proxy fronts frontend and API for production-style routing.
```

## Tech Stack

Frontend: Next.js, React, TypeScript, Tailwind CSS, React Flow, TanStack Query, Zustand, Recharts.

Backend: Python, FastAPI, SQLAlchemy, Alembic, Pydantic, JWT auth, RBAC, Celery, Redis, Prometheus metrics.

Infrastructure: Docker Compose, Nginx, PostgreSQL, Redis, Prometheus, Grafana, GitHub Actions, Terraform templates for AWS.

## Features

- JWT authentication with refresh-token structure and bcrypt password hashing.
- Roles: admin, developer, viewer.
- Workflow CRUD, graph validation, versioning, publish, rollback, manual runs.
- DAG validation for cycles, disconnected nodes, invalid edges, missing triggers, and node configuration.
- Execution planner with topological levels for parallelizable groups.
- Celery-ready worker system plus inline local execution for instant demo feedback.
- Retry, cancel, logs, artifacts, notification events, dead-letter records.
- AI nodes for summarization, classification, and JSON generation with deterministic local fallback.
- Health, readiness, metrics, worker heartbeat, queue depth, analytics.
- React Flow builder with node palette, side-panel config, validation, save, publish, and run.

## Screenshots

The repository includes screenshots from the local demo environment:

| Dashboard | Workflow Builder |
| --- | --- |
| ![Dashboard](docs/screenshots/dashboard.png) | ![Workflow Builder](docs/screenshots/workflow-builder.png) |

| Execution Detail | Worker Health |
| --- | --- |
| ![Execution Detail](docs/screenshots/execution-detail.png) | ![Worker Health](docs/screenshots/worker-health.png) |

You can also run the app and open:

- Dashboard: http://localhost:3000
- Workflow Builder: http://localhost:3000/workflows/builder
- Analytics: http://localhost:3000/analytics
- Worker Health: http://localhost:3000/workers

## Demo Walkthrough

1. Start the stack with `docker compose up --build`.
2. Open http://localhost:3000 and sign in as the Admin demo user.
3. Open **Workflows** and run `Customer Support AI Triage`.
4. Open **Executions** and select the new execution.
5. Inspect node status, attempts, timing, logs, and artifacts.
6. Open **Workflow Builder** to validate, save, publish, and run a visual DAG.
7. Open **Worker Health** and **Analytics** to review queue and reliability signals.

## Local Setup

```bash
docker compose up --build
```

After startup:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

## Demo Credentials

Admin:
email: admin@flowforge.dev
password: Password123!

Developer:
email: developer@flowforge.dev
password: Password123!

Viewer:
email: viewer@flowforge.dev
password: Password123!

## API Documentation

Swagger is available at http://localhost:8000/docs. See [docs/api.md](docs/api.md) for an endpoint overview.

## Architecture Decisions

See [docs/decisions.md](docs/decisions.md) for the main design decisions and tradeoffs behind the stack, local execution model, deterministic AI fallback, and visual builder.

## Worker Architecture

Executions are represented as persisted workflow runs with node execution rows. The planner converts the saved DAG into topological levels. Independent nodes in the same level are parallelizable by Celery workers; the local demo executes them inline so no paid or external service is required. Workers record heartbeats, logs, outputs, artifacts, retries, and dead-letter failures.

## Database Schema Summary

Core tables include users, roles, workflows, workflow_versions, workflow_nodes, workflow_edges, executions, node_executions, execution_logs, execution_artifacts, schedules, worker_heartbeats, audit_logs, api_keys, dead_letter_tasks, notification_events, and system_metrics.

## Testing

```bash
./scripts/test.sh
```

Backend tests use Pytest. Frontend tests use Vitest and React Testing Library.

## Deployment

Use Docker Compose for local and single-host deployments. For AWS, start with the Terraform templates in `infra/terraform`, then deploy containers to ECS, PostgreSQL to RDS, Redis to ElastiCache, and route traffic through an ALB or Nginx.

## Future Improvements

- True distributed fan-out/fan-in execution with Celery chords.
- WebSocket live execution updates.
- OAuth providers.
- More node integrations.
- Multi-tenant workspace isolation.

## Known Limitations

- The local demo executes workflows inline after creating persisted execution records so the UI responds immediately. The worker queue is wired for Celery, but full distributed fan-out/fan-in is a future hardening step.
- OAuth-ready structures are present, but external OAuth providers are not connected.
- Notification nodes simulate email and Slack delivery locally and store notification events in the database.
- AI nodes use deterministic local fallbacks unless `OPENAI_API_KEY` is provided.
- Terraform templates are deployment starters, not a complete production landing zone.
