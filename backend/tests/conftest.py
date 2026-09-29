import os
import sys
import tempfile

import pytest

# Isolated temp SQLite DB + audit log per test session, so tests never touch dev data.
_tmp_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["AUDIT_LOG_PATH"] = f"{_tmp_dir}/audit.log.jsonl"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.seed import seed  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from app.auth.jwt_utils import create_access_token  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    seed()
    yield


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def two_customers(db_session):
    customers = db_session.query(models.Customer).limit(2).all()
    return customers[0], customers[1]


@pytest.fixture
def token_for():
    def _make(customer_id):
        return create_access_token(customer_id=customer_id, role="CUSTOMER")
    return _make
