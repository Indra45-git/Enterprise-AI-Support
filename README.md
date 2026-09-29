# Enterprise AI Customer Support Agent & Embeddable Chatbot SaaS

A security-first, agentic AI customer support platform built on the `AI_Agent_100_Users_DB_Dataset` (100 customers, 20 products, 300 orders, 569 order items, 100 support tickets) with an **embeddable chat widget** that can be embedded on any website (Next.js, WordPress, Shopify, Webflow, HTML) in one line of code.

**Core design principle: The LLM is an untrusted reasoning component, not a security boundary.** It can only request approved tools; a Tool Gateway independently enforces authentication, authorization, schema validation, deterministic business rules, and audit logging before anything touches the database.

---

## 🚀 Key Features

* **🔌 1-Line Embeddable Chatbot Widget (`widget.js`)**:
  * Drop `<script src="https://your-domain.vercel.app/widget.js" data-bot-id="default"></script>` on any external website.
  * Customizable floating launcher, colors, avatar, prompt chips, and responsive drawer on mobile.
* **🎨 Chatbot Studio & Customizer (`/settings` API)**:
  * Real-time preview of chatbot brand color, welcome message, avatar icon, and starter questions.
  * Live interactive mockup device allowing instant testing of the widget.
* **🤖 Multi-LLM Support (Gemini API, Claude, OpenAI, Offline Fallback)**:
  * Google Gemini API (`GEMINI_API_KEY` / `GOOGLE_API_KEY`) for intelligent responses.
  * Anthropic Claude (`ANTHROPIC_API_KEY`).
  * Deterministic rule router and RAG engine that works 100% offline without API keys for testing and evaluation.
* **🛡️ Security Guardrails & Cross-Tenant Isolation**:
  * Blocks prompt injection, jailbreaks, and PII scraping deterministically.
  * Customers cannot access orders or tickets belonging to other accounts.
* **📦 Live ERP & Order Resolution**:
  * Automated order tracking, delivery status, and 10-day return eligibility checks based on policy.
* **🎫 Support Ticket Management**:
  * List, create, and escalate support tickets to human supervisor queue.
* **🌐 Production-Ready Vercel Deployment**:
  * Configured with `vercel.json` and `api/index.py` serverless runtime with automatic SQLite `/tmp` migration.

---

## 🛠️ Quick Start (Local Development)

```powershell
# 1. Activate virtual environment
.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate     # macOS/Linux

# 2. Seed database (loads 100 customers, products, orders, tickets, and bot settings)
cd backend
python -m app.seed

# 3. Start development server
python -m uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` or open `frontend/index.html` in your browser.
* Use 1-click customer login chips, or enter any seeded email (`user010@example.com`, `user001@example.com`, etc.) with password `demo1234`.
* Test the external embedded widget demo at `frontend/embed-demo.html` or `http://localhost:8000/embed-demo.html`.

---

## 🧪 Run Tests

```powershell
cd backend
python -m pytest -q
# 27 tests covering auth, authorization, business rules, guardrails, agent flow, settings, and public widget
```

---

## ☁️ Deploy to Vercel

1. Push your repository to GitHub, GitLab, or Bitbucket.
2. In the [Vercel Dashboard](https://vercel.com/new):
   * Click **"Add New Project"** and select your repository.
   * Framework Preset: Leave as **Other**.
   * Root Directory: Leave as `./` (root).
3. Optional Environment Variables in Vercel:
   * `GEMINI_API_KEY`: Your Google Gemini API Key.
   * `JWT_SECRET`: A secure random secret string.
   * `DATABASE_URL`: (Optional) Point to external PostgreSQL / Supabase for production, or omit to run out-of-the-box with the pre-seeded SQLite database.
4. Click **Deploy**!

Once deployed, your full-stack app, dashboard, and embeddable widget will be live:
* Web Dashboard: `https://your-project.vercel.app`
* Embed Script for Clients: `https://your-project.vercel.app/widget.js`
* External Website Demo: `https://your-project.vercel.app/embed-demo.html`
* API Documentation: `https://your-project.vercel.app/docs`

---

## 📋 Embed Code Snippet

Any website owner can add your AI support chatbot by pasting this snippet before `</body>`:

```html
<!-- Enterprise AI Customer Support Chatbot -->
<script src="https://your-domain.vercel.app/widget.js" data-bot-id="default" data-api-url="https://your-domain.vercel.app"></script>
```
