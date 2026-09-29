# Evaluation

`backend/tests/` is the evaluation suite (run with `pytest -q` from `backend/`):

- `test_auth.py` - login success/failure, chat requires auth
- `test_authorization.py` - cross-tenant denial, own-resource access, malformed/injection-
  like id rejected by schema validation
- `test_business_rules.py` - return eligibility (not delivered, within window, past window,
  non-returnable product), cancellation eligibility, deterministic ticket priority mapping
- `test_guardrails.py` - prompt injection block, bulk-data-request block, normal question
  allowed, output PII block, indirect injection in a retrieved doc neutralized
- `test_agent_flow.py` - full chat flow: order-status lookup end to end, prompt injection
  blocked mid-conversation, cross-tenant order lookup denied through the agent (not just
  the raw API)

21/21 passing at last run. For a production evaluation harness per the original spec,
extend this suite with: hallucination checks (does the reply only state facts present in
the tool result), a larger red-team prompt-injection corpus, and metrics aggregation
(Task Success Rate, Grounded Answer Rate, PII Leakage Rate, Unauthorized Tool Call Rate,
Prompt Injection Detection Rate, False Positive Rate, latency/cost) computed from the
audit log + `/metrics-snapshot`.
