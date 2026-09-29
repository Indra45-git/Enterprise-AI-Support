"""
Agent orchestration loop.

Customer -> input guardrail -> RAG (for policy questions) -> LLM decides a tool or a final
answer -> Tool Gateway (auth + business rules + audit) -> LLM composes final answer from the
tool result -> output guardrail -> Customer.

This loop plays the role LangGraph would in production (a small state graph with
retry/branching). It is implemented directly here to avoid pulling in a heavy dependency
for the sandboxed demo; the state machine below is exactly the graph the spec describes
(agent/graph.py, agent/state.py, agent/router.py collapsed into one place for clarity) and
can be lifted into LangGraph nodes 1:1 if you want to swap it in.
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.auth.dependencies import Identity
from app.guardrails import guardrails
from app.rag.retriever import retrieve
from app.rag.security import build_context_block
from app.agent.llm_client import decide_next_step, NextStep
from app.tools.tool_gateway import call_tool, ToolError
from app.observability.metrics import increment

MAX_TOOL_HOPS = 3
POLICY_KEYWORDS = ["policy", "return window", "refund", "warranty", "shipping", "cancellation",
                    "sla", "how long", "eligible", "can i return", "can i cancel"]


@dataclass
class AgentResponse:
    reply: str
    tool_calls: list[str] = field(default_factory=list)
    blocked: bool = False
    blocked_reason: str = ""


def handle_message(message: str, identity: Identity, db: Session, session_id: str,
                   *, customer_name: str | None = None) -> AgentResponse:
    # 1. Input guardrail
    input_check = guardrails.check_input(message)
    increment("guardrail.input.checked")
    if not input_check.allowed:
        increment(f"guardrail.input.blocked.{input_check.category}")
        return AgentResponse(reply=input_check.reason, blocked=True, blocked_reason=input_check.category)

    # 2. RAG - only pull policy context when the question looks policy-related, to keep
    #    context minimal (data minimization applies to retrieved context too).
    context_block = ""
    if any(k in message.lower() for k in POLICY_KEYWORDS):
        chunks = retrieve(message, k=2)
        context_block = build_context_block(chunks)
        if chunks:
            increment("rag.retrieval.hits")

    # 3. Greeting detection — handle casual greetings before the tool loop
    greeting_words = ["hi", "hello", "hey", "hii", "hiii", "greetings", "good morning",
                      "good afternoon", "good evening", "howdy", "sup", "yo", "namaste"]
    stripped = message.strip().rstrip("!.,?").lower()
    if stripped in greeting_words:
        display_name = customer_name.split()[0] if customer_name else "there"
        greeting_reply = (
            f"Hello, {display_name}! 👋 How can I help you today?\n\n"
            "Here's what I can assist with:\n"
            "- 📦 **Order status & details** — share an order ID e.g. *ORD00012*\n"
            "- 🔄 **Return eligibility** — share an order & product ID\n"
            "- 🎫 **Support tickets** — say *\"open a ticket\"* or share a ticket ID\n"
            "- 🛒 **Product info** — share a product ID e.g. *PROD0005*"
        )
        return AgentResponse(reply=greeting_reply)

    # 4. Tool loop
    history = [{"role": "user", "content": message}]
    tool_calls_made: list[str] = []
    final_text = None

    for _ in range(MAX_TOOL_HOPS):
        step: NextStep = decide_next_step(history, context_block,
                                           customer_name=customer_name,
                                           customer_id=identity.customer_id)
        if step.kind == "final":
            final_text = step.text
            # If this was a policy question and the router (in offline/no-API-key mode)
            # had nothing more specific to say, answer straight from the retrieved
            # policy context instead of a generic fallback line.
            if context_block and (final_text is None or "could you share an order ID" in final_text.lower()):
                final_text = _answer_from_policy(context_block)
            break

        tool_calls_made.append(step.tool_name)
        try:
            result = call_tool(step.tool_name, step.tool_args or {}, identity, db, session_id=session_id)
            observation = f"Tool {step.tool_name} succeeded: {result['data']}"
        except ToolError as e:
            observation = f"Tool {step.tool_name} failed ({e.code}): {e.message}"

        history.append({"role": "assistant", "content": f"[called {step.tool_name} with {step.tool_args}]"})
        history.append({"role": "user", "content": f"[tool result] {observation}\nNow answer the customer plainly in one or two sentences, based only on this result."})

        # For the offline rule-based router, compose the final answer directly from the
        # observation rather than looping again (keeps the demo deterministic and fast).
        final_text = _summarize_observation(step.tool_name, observation)
        break

    if final_text is None:
        final_text = "I couldn't complete that request. Could you rephrase it?"

    # 4. Output guardrail
    output_check = guardrails.check_output(final_text)
    if not output_check.allowed:
        increment(f"guardrail.output.blocked.{output_check.category}")
        return AgentResponse(reply=output_check.reason, tool_calls=tool_calls_made,
                              blocked=True, blocked_reason=output_check.category)

    return AgentResponse(reply=final_text, tool_calls=tool_calls_made)


def _answer_from_policy(context_block: str) -> str:
    """Offline-mode fallback: surface the full retrieved policy content with a proper heading.
    With ANTHROPIC_API_KEY set, the real LLM composes a richer conversational answer instead."""
    lines = context_block.splitlines()
    sections: list[tuple[str, list[str]]] = []  # [(title, [body lines])]
    current_title = ""
    current_body: list[str] = []

    for line in lines:
        stripped = line.strip()
        # Skip envelope wrappers
        if stripped.startswith("<") or stripped.startswith("The block above") or not stripped:
            continue
        # Document marker e.g. [doc: warranty_policy]
        if stripped.startswith("[doc:"):
            if current_body:
                sections.append((current_title, current_body))
            current_title = stripped.strip("[]").replace("doc:", "").strip().replace("_", " ").title()
            current_body = []
            continue
        # Markdown heading inside the doc → use as section title
        if stripped.startswith("#"):
            current_title = stripped.lstrip("#").strip()
            continue
        current_body.append(stripped)

    if current_body:
        sections.append((current_title, current_body))

    if not sections:
        return "I couldn't find a specific policy for that. I can open a support ticket if you'd like a human to confirm."

    parts = []
    seen_titles: set[str] = set()
    for title, body in sections:
        if title in seen_titles:
            continue
        seen_titles.add(title)
        body_text = " ".join(body)
        if title:
            parts.append(f"**{title}**\n{body_text}")
        else:
            parts.append(body_text)

    return "\n\n".join(parts)


def _format_value(v) -> str:
    if v is None or v == "None":
        return "—"
    return str(v)


def _format_order(o: dict) -> str:
    items = o.get("items", [])
    items_line = ""
    if items:
        parts = ", ".join(
            f"{i['product_name']} ×{i['quantity']}" if i.get("quantity", 1) > 1 else i["product_name"]
            for i in items
        )
        items_line = f"**Items:** {parts}  \n"
    return (
        f"**Order:** {o.get('order_id','—')}  \n"
        f"**Status:** {o.get('status','—')}  \n"
        f"**Total:** ₹{o.get('total_amount','—')}  \n"
        f"{items_line}"
        f"**Payment:** {o.get('payment_status','—')} via {o.get('payment_method','—')}  \n"
        f"**Order Date:** {o.get('order_date','—')}  \n"
        f"**Expected Delivery:** {_format_value(o.get('expected_delivery'))}  \n"
        f"**Tracking:** {_format_value(o.get('tracking_number'))}  \n"
        f"**Cancellable:** {'Yes' if o.get('cancellable') else 'No'}"
    )


def _format_ticket(t: dict) -> str:
    order_line = f"**Order:** {t.get('order_id')}  \n" if t.get('order_id') else ""
    esc_line = f"**Escalation Reason:** {t.get('escalation_reason')}  \n" if t.get('escalation_reason') else ""
    assigned_line = f"**Assigned To:** {t.get('assigned_to')}  \n" if t.get('assigned_to') else ""
    return (
        f"**Ticket:** {t.get('ticket_id','—')}  \n"
        f"**Issue:** {t.get('issue_type','—')}  \n"
        f"**Status:** {t.get('status','—')}  \n"
        f"**Priority:** {t.get('priority','—')}  \n"
        f"{assigned_line}"
        f"{order_line}"
        f"{esc_line}"
        f"**Created:** {t.get('created_at','—')}"
    )


def _format_product(p: dict) -> str:
    name = p.get('product_name') or p.get('name') or p.get('product_id', '—')
    prod_id = f" ({p.get('product_id')})" if p.get('product_id') and p.get('product_id') != name else ""
    stock_val = p.get('stock_quantity')
    if stock_val is not None:
        stock = f"{stock_val} units ({'In Stock' if stock_val > 0 else 'Out of Stock'})"
    else:
        stock = "In Stock" if p.get('in_stock') else ("Out of Stock" if p.get('in_stock') is False else "—")
    warranty = f"{p.get('warranty_months')} months" if p.get('warranty_months') is not None else "—"
    return (
        f"**Product:** {name}{prod_id}  \n"
        f"**Category:** {p.get('category','—')}  \n"
        f"**Price:** ₹{p.get('price','—')}  \n"
        f"**Stock:** {stock}  \n"
        f"**Warranty:** {warranty}  \n"
        f"**Returnable:** {'Yes' if p.get('returnable') else 'No'}"
    )


def _pretty_data(tool_name: str, data) -> str:
    """Convert raw tool result data into clean markdown."""
    import json, ast

    # If it's a string representation of a Python literal, parse it
    if isinstance(data, str):
        try:
            data = ast.literal_eval(data)
        except Exception:
            pass

    # Handle dict wrappers like {'orders': [...]} or {'ticket': {...}}
    if isinstance(data, dict):
        # Unwrap single-key dicts
        if len(data) == 1:
            key, val = next(iter(data.items()))
            data = val

    # List of items
    if isinstance(data, list) and data and isinstance(data[0], dict):
        # Detect type by keys (check ticket_id and product_id before order_id, since tickets have order_id)
        sample = data[0]
        if 'ticket_id' in sample:
            parts = [_format_ticket(t) for t in data]
            return "\n\n---\n\n".join(parts)
        if 'product_id' in sample:
            parts = [_format_product(p) for p in data]
            return "\n\n---\n\n".join(parts)
        if 'order_id' in sample:
            parts = [_format_order(o) for o in data]
            return "\n\n---\n\n".join(parts)
        # Generic list of dicts
        rows = []
        for item in data:
            rows.append("  \n".join(f"**{k}:** {_format_value(v)}" for k, v in item.items()))
        return "\n\n---\n\n".join(rows)

    # Single dict
    if isinstance(data, dict):
        if 'ticket_id' in data:
            return _format_ticket(data)
        if 'product_id' in data:
            return _format_product(data)
        if 'order_id' in data:
            return _format_order(data)
        return "  \n".join(f"**{k}:** {_format_value(v)}" for k, v in data.items())

    # Scalar
    return str(data)


def _summarize_observation(tool_name: str, observation: str) -> str:
    """Deterministic, honest templating: never claims success unless the tool said so."""
    if "failed" in observation.split(":")[0]:
        # e.g. "Tool get_order_status failed (forbidden): ..."
        reason = observation.split(":", 1)[1].strip() if ":" in observation else observation
        return f"I couldn't do that: {reason}"
    data_str = observation.split(":", 1)[1].strip() if ":" in observation else observation
    formatted = _pretty_data(tool_name, data_str)
    tool_label = tool_name.replace("_", " ").title()
    return f"### {tool_label}\n\n{formatted}"

