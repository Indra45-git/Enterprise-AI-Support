# Architecture

## Core principle
**The LLM is an untrusted reasoning component, not a security boundary.**
It may only *suggest* a tool call; every tool call is independently authenticated,
authorized, validated, and checked against deterministic business rules before it
touches the database.

## Request flow
```
Customer -> React/HTML client -> FastAPI
  -> Auth (JWT verified server-side, customer_id extracted from token only)
  -> Input Guardrail (guardrails/guardrails.py; NeMo-compatible interface)
  -> Agent loop (agent/agent.py): RAG for policy Qs, LLM/rule-router decides a tool
  -> Tool Gateway (tools/tool_gateway.py):
       schema validation -> rate limit -> ownership/authz check
       -> business rules (services/policy_service.py) -> idempotency (writes)
       -> service layer -> parameterized SQLAlchemy ORM -> DB
  -> Audit log (audit/audit_logger.py) on every call, success or failure
  -> Output Guardrail (PII leak check, no unsupported success claims)
  -> Customer
```

## Why the dataset maps this way
The provided `AI_Agent_100_Users_DB_Dataset` (customers, products, orders, order_items,
support_tickets) is explicitly labelled "relational data for an AI Customer Support Agent"
(see its README), so the schema in `backend/app/models.py` mirrors the CSVs 1:1, and the
eight tools in `tools/definitions.py` map directly onto the natural questions that data
supports (order status, order details, product info, return eligibility, ticket status,
ticket creation, escalation).

## Sandbox-vs-production trade-offs (read this before grading/deploying)
This was built and tested inside a sandboxed environment without a live Postgres+pgvector
cluster, Redis, or a NeMo Guardrails model available. Every component keeps the *same
interface* the full spec calls for, with a lightweight local implementation behind it:

| Component        | Here (runs anywhere, no external services)         | Swap in for production |
|-------------------|-----------------------------------------------------|--------------------------|
| Database          | SQLite via SQLAlchemy (`DATABASE_URL`)              | Postgres (`docker-compose.yml` ships `ankane/pgvector`) |
| Vector search      | Dependency-free TF-IDF cosine index (`rag/retriever.py`) | pgvector similarity search, same `retrieve()` signature |
| Guardrails        | Regex/heuristic rules (`guardrails/guardrails.py`), same `check_input`/`check_output` contract | NVIDIA NeMo Guardrails - config stub in `guardrails/nemo_config/` |
| Rate limit / idempotency | In-process dict (`tools/tool_gateway.py`)      | Redis token bucket / SETNX |
| Agent orchestration | A bounded loop in `agent/agent.py`, real Anthropic tool-calling when `ANTHROPIC_API_KEY` is set, deterministic rule-based router otherwise | LangGraph state graph (the loop maps 1:1 onto graph nodes) |
| Observability     | In-memory counters/timers, `/metrics-snapshot`       | OpenTelemetry + Prometheus + Grafana |

Everything else — JWT auth, RBAC, ownership checks, deterministic business rules, the
Tool Gateway's validation pipeline, audit logging, idempotency, retrieval-security
sanitization, and the input/output guardrail checkpoints — is real, not stubbed, and is
covered by the test suite in `backend/tests/`.
