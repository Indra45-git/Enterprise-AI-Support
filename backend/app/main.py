from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth_routes, chat_routes, orders_routes, products_routes, tickets_routes, settings_routes
from app.observability.metrics import snapshot

app = FastAPI(
    title="Enterprise AI Customer Support Agent",
    description="Security-first agentic support platform with embeddable SaaS chatbot.",
    version="0.2.0",
)

# Open CORS to support embeddable widget on third-party domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(orders_routes.router)
app.include_router(products_routes.router)
app.include_router(tickets_routes.router)
app.include_router(settings_routes.router)

from app.database import get_db

# Aliases for widget compatibility
@app.post("/widget/chat", tags=["widget"])
def widget_chat_alias(payload: chat_routes.schemas.ChatRequest, db=Depends(get_db)):
    return chat_routes.public_chat(payload, db=db)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


@app.get("/metrics-snapshot")
def metrics_snapshot():
    return snapshot()


@app.get("/policies")
def list_policies():
    """Returns official enterprise policies and SLA documentation from knowledge base."""
    kb_dir = Path(__file__).resolve().parent.parent.parent / "knowledge_base"
    if not kb_dir.exists():
        kb_dir = Path(__file__).resolve().parent.parent / "knowledge_base"
    meta = [
        {
            "filename": "return_policy.md",
            "title": "Enterprise Return Policy",
            "category": "returns",
            "badge": "10-Day Window",
            "icon": "📦",
            "prompt": "What is the return policy window and eligibility criteria?"
        },
        {
            "filename": "refund_policy.md",
            "title": "Automated Refund Policy",
            "category": "refunds",
            "badge": "3-5 Business Days",
            "icon": "💳",
            "prompt": "How long do refunds take and what payment methods receive them?"
        },
        {
            "filename": "shipping_policy.md",
            "title": "Shipping & Fulfillment SLA",
            "category": "shipping",
            "badge": "Standard & Express",
            "icon": "🚚",
            "prompt": "What are the shipping delivery times and carrier partners?"
        },
        {
            "filename": "cancellation_policy.md",
            "title": "Order Cancellation Policy",
            "category": "cancellations",
            "badge": "Pre-Dispatch Only",
            "icon": "🚫",
            "prompt": "Can I cancel an order that has already shipped?"
        },
        {
            "filename": "warranty_policy.md",
            "title": "Manufacturer Warranty Policy",
            "category": "warranty",
            "badge": "12-24 Months",
            "icon": "🛡️",
            "prompt": "What does the hardware warranty cover on electronics?"
        },
        {
            "filename": "support_sla.md",
            "title": "Support Escalation & SLA Matrix",
            "category": "sla",
            "badge": "Tier 1 < 2s · Tier 2 < 3h",
            "icon": "⚡",
            "prompt": "What are your support SLAs and escalation matrix?"
        },
        {
            "filename": "product_faq.md",
            "title": "Product Catalog & Invoicing FAQ",
            "category": "faq",
            "badge": "Verified FAQ",
            "icon": "❓",
            "prompt": "Where can I download GST tax invoices and verify warranty?"
        }
    ]
    results = []
    for item in meta:
        file_path = kb_dir / item["filename"]
        content = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
        lines = [line.strip() for line in content.split("\n") if line.strip() and not line.strip().startswith("#")]
        summary = lines[0] if lines else "Official company policy documentation."
        results.append({
            "filename": item["filename"],
            "title": item["title"],
            "category": item["category"],
            "badge": item["badge"],
            "icon": item["icon"],
            "summary": summary,
            "prompt": item["prompt"],
            "content": content
        })
    return results


# Serve frontend static assets (index.html, style.css, app.js, widget.js, embed-demo.html)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")
