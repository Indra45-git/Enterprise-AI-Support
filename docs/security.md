# Security & Threat Model

## Defense in depth
Authentication -> Authorization -> Input Guardrails -> Tool Schema Validation ->
Business Rules -> Data Minimization -> Output Guardrails -> Audit Logging -> Observability

## Threats addressed
- **Prompt injection / jailbreak**: input guardrail regex set (`guardrails.py`); test in
  `test_guardrails.py::test_blocks_prompt_injection`.
- **Indirect prompt injection via RAG documents**: `rag/security.py` redacts
  instruction-like phrases from retrieved chunks and wraps them in an explicit
  "untrusted data" envelope before they reach the LLM; see
  `test_guardrails.py::test_indirect_injection_in_retrieved_doc_is_neutralized`.
- **Horizontal privilege escalation** (customer A reading customer B's order/ticket):
  every tool that takes an order/ticket id runs an ownership check in
  `tools/tool_gateway.py::_owned_order` / `_owned_ticket`, independent of what the LLM
  claims; covered by `test_authorization.py`.
- **SQL injection / arbitrary SQL**: the LLM never sees a SQL interface. All ids are
  validated with strict Pydantic regex patterns (`schemas.py`) before touching the ORM;
  no raw SQL is ever built from user or LLM input.
- **Bulk PII exfiltration** ("give me all customers' emails"): blocked by the input
  guardrail's sensitive-data pattern set, independent of tool access.
- **Output PII leakage**: output guardrail scans the composed reply for email/phone/card
  -like patterns before it's returned.
- **False success claims**: the agent only ever summarizes an actual tool result
  (`agent.py::_summarize_observation`); it cannot say an action succeeded without a
  successful `ToolError`-free tool response.
- **Abuse / DoS**: per-customer rate limiting in the Tool Gateway (swap for Redis token
  bucket at scale).
- **Duplicate writes**: `create_support_ticket` accepts an idempotency key and returns
  the existing ticket instead of creating a duplicate on retry.

## Not implemented in this sandbox build (see architecture.md for swap-in path)
Full NVIDIA NeMo Guardrails model, live Postgres+pgvector, Redis, OpenTelemetry/Prometheus/
Grafana, and a LangGraph-based orchestrator - all have config stubs or drop-in interfaces
ready, but weren't run against live infrastructure here.
