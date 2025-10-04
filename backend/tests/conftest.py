import os
import sys
from pathlib import Path
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
TEST_DB_PATH = TESTS_DIR / "test.db"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# usa SQLite isolado para a suíte de testes
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

from app.main import app  # noqa: E402
from app.db.database import Base, SessionLocal, engine, get_db  # noqa: E402


def override_get_db() -> Iterator[Session]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# injeta a sessão de teste no app
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    # recria o schema a cada teste
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_db_file() -> Iterator[None]:
    # remove o arquivo SQLite ao final da sessão
    yield
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture
def client() -> Iterator[TestClient]:
    # TestClient faz o bridge ASGI corretamente (sem precisar lidar com transports)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
