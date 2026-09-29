"""Vercel serverless function entrypoint.

Vercel's Python runtime expects an `app` variable (ASGI/WSGI) in api/index.py.
This file imports and re-exports the FastAPI app so it works as a Vercel
serverless function handling all API routes.
"""
import sys
import os
import shutil
from pathlib import Path

# Add the backend directory to the Python path so all imports resolve
root_dir = Path(__file__).resolve().parent.parent
backend_dir = str(root_dir / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Mark serverless environment
os.environ["VERCEL"] = "1"

# In Vercel serverless functions, copy the pre-seeded SQLite DB to writable temp if needed
import tempfile
tmp_dir = Path("/tmp") if (Path("/tmp").exists() and os.access("/tmp", os.W_OK)) else Path(tempfile.gettempdir())
tmp_db = tmp_dir / "app.db"
orig_db = root_dir / "backend" / "app.db"
if orig_db.exists() and not tmp_db.exists():
    try:
        tmp_db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(orig_db, tmp_db)
    except Exception:
        pass

# pyright: reportMissingImports=false
from app.main import app  # noqa: E402  # type: ignore[import-untyped, missing-import]

# Ensure models & tables are ready and seeded if needed
try:
    from app.database import engine, Base, SessionLocal  # type: ignore[import-untyped, missing-import]
    from app import models  # noqa: F401  # type: ignore[import-untyped, missing-import]
    Base.metadata.create_all(bind=engine)

    need_seed = False
    db = SessionLocal()
    try:
        need_seed = (db.query(models.Customer).count() == 0)
    except Exception:
        need_seed = True
    finally:
        db.close()

    if need_seed:
        try:
            from app.seed import seed  # type: ignore[import-untyped, missing-import]
            seed()
        except Exception:
            pass
except Exception:
    pass


