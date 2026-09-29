"""
The exact list of approved business capabilities the LLM may request.
customer_id is intentionally NOT a parameter anywhere here - it always comes
from the authenticated session (see auth/dependencies.py), never from the model.
"""

TOOL_SPECS = [
    {
        "name": "get_my_orders",
        "description": "List the authenticated customer's own orders.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_order_status",
        "description": "Get the status and expected delivery of one of the customer's orders.",
        "input_schema": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "e.g. ORD00012"}},
            "required": ["order_id"]},
    },
    {
        "name": "get_order_details",
        "description": "Get full details (items, amounts, payment, tracking) of one of the customer's orders.",
        "input_schema": {"type": "object", "properties": {
            "order_id": {"type": "string"}}, "required": ["order_id"]},
    },
    {
        "name": "get_product_details",
        "description": "Get product info: price, category, stock, warranty length, returnable flag.",
        "input_schema": {"type": "object", "properties": {
            "product_id": {"type": "string", "description": "e.g. PROD0007"}},
            "required": ["product_id"]},
    },
    {
        "name": "check_return_eligibility",
        "description": "Deterministically check whether a product in an order is eligible for return right now.",
        "input_schema": {"type": "object", "properties": {
            "order_id": {"type": "string"}, "product_id": {"type": "string"}},
            "required": ["order_id", "product_id"]},
    },
    {
        "name": "get_my_tickets",
        "description": "List all support tickets submitted by the authenticated customer.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_ticket_status",
        "description": "Get the status/priority/assignment of one of the customer's support tickets.",
        "input_schema": {"type": "object", "properties": {
            "ticket_id": {"type": "string"}}, "required": ["ticket_id"]},
    },
    {
        "name": "create_support_ticket",
        "description": "Open a new support ticket for the customer. Priority is assigned by backend policy, not by you.",
        "input_schema": {"type": "object", "properties": {
            "issue_type": {"type": "string", "enum": [
                "Wrong item", "Missing item", "Delivery complaint", "Damaged item",
                "Refund pending", "Payment issue", "Product query", "Cancellation request", "Other"]},
            "description": {"type": "string"},
            "order_id": {"type": "string", "description": "optional, if related to an order"},
        }, "required": ["issue_type", "description"]},
    },
    {
        "name": "escalate_ticket",
        "description": "Escalate an existing ticket to a human support agent, with a reason.",
        "input_schema": {"type": "object", "properties": {
            "ticket_id": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["ticket_id", "reason"]},
    },
]

TOOL_NAMES = [t["name"] for t in TOOL_SPECS]
