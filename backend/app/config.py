"""
Central configuration.

Swap points for production:
- DATABASE_URL -> point to Postgres, e.g. postgresql+psycopg2://user:pass@host/db
- REDIS_URL -> used by rate_limit / idempotency modules when USE_REDIS=true
- ANTHROPIC_API_KEY / OPENAI_API_KEY -> enables real LLM tool-calling in agent/llm_client.py
  (without a key, the agent falls back to a deterministic rule-based intent router so the
  whole system still runs end-to-end offline/for grading).
"""
import os
from pathlib import Path
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent

# Detect Vercel / AWS Lambda serverless environment (read-only filesystem except /tmp)
IS_VERCEL = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

if IS_VERCEL and not os.getenv("DATABASE_URL"):
    # On Vercel / serverless, copy app.db to writable /tmp so SQLite has write permissions
    import tempfile
    tmp_dir = Path("/tmp") if (Path("/tmp").exists() and os.access("/tmp", os.W_OK)) else Path(tempfile.gettempdir())
    tmp_db = tmp_dir / "app.db"
    orig_db = BASE_DIR / "app.db"
    if orig_db.exists() and not tmp_db.exists():
        try:
            tmp_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(orig_db, tmp_db)
        except Exception:
            pass
    posix_path = tmp_db.resolve().as_posix()
    DATABASE_URL = f"sqlite:///{posix_path}" if posix_path.startswith("/") else f"sqlite:///{posix_path}"

else:
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'app.db'}")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo1234")  # seeded for every customer, demo only

# LLM Providers (Gemini from tutorial, Anthropic, OpenAI, or deterministic offline fallback)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

USE_REDIS = os.getenv("USE_REDIS", "false").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

if IS_VERCEL:
    AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", "/tmp/audit.log.jsonl")
else:
    AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", str(BASE_DIR / "audit.log.jsonl"))

RETURN_WINDOW_DAYS = int(os.getenv("RETURN_WINDOW_DAYS", "10"))
ESCALATION_WAIT_DAYS = int(os.getenv("ESCALATION_WAIT_DAYS", "3"))
