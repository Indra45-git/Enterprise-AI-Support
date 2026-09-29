"""Vercel serverless function entrypoint.

Vercel's Python runtime expects an `app` variable (ASGI/WSGI) in api/index.py.
This file imports and re-exports the FastAPI app so it works as a Vercel
serverless function handling all API routes.
"""
import sys
import os
import shutil
from pathlib import Path

# Dynamically locate the project root and backend directory across local and Vercel environments
this_file = Path(__file__).resolve()
if this_file.parent.name == "api":
    root_dir = this_file.parent.parent
else:
    root_dir = this_file.parent

possible_backend_dirs = [
    root_dir / "backend",
    this_file.parent / "backend",
    this_file.parent.parent / "backend",
    Path.cwd() / "backend",
    Path("/var/task/backend"),
    Path("/var/task"),
]

backend_dir = None
for candidate in possible_backend_dirs:
    if candidate.exists() and (candidate / "app").exists():
        backend_dir = candidate
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
        break

# In Vercel serverless functions, copy the pre-seeded SQLite DB to writable temp if needed
import tempfile
tmp_dir = Path("/tmp") if (Path("/tmp").exists() and os.access("/tmp", os.W_OK)) else Path(tempfile.gettempdir())
tmp_db = tmp_dir / "app.db"

possible_orig_dbs = [
    (backend_dir / "app.db") if backend_dir else None,
    root_dir / "backend" / "app.db",
    Path("/var/task/backend/app.db"),
    Path.cwd() / "backend" / "app.db",
]
for candidate_db in possible_orig_dbs:
    if candidate_db and candidate_db.exists() and not tmp_db.exists():
        try:
            tmp_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate_db, tmp_db)
            break
        except Exception:
            pass

# pyright: reportMissingImports=false
try:
    from app.main import app  # noqa: E402  # type: ignore[import-untyped, missing-import]
except Exception as exc:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    app = FastAPI(title="Diagnostic Startup App")
    startup_tb = traceback.format_exc()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    def startup_error(path: str):
        return PlainTextResponse(f"Vercel Serverless Function Startup Error:\n{startup_tb}", status_code=500)

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



