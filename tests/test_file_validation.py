import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import api.app as app_module
from api.app import app
from api.auth import get_current_user
from api import users


@pytest.fixture(scope="module", autouse=True)
def setup_test_db(tmp_path_factory):
    """Setup test database for file validation tests."""
    tmp_path = tmp_path_factory.mktemp("data")
    db_path = tmp_path / "users.db"
    vector_path = tmp_path / "vectors"

    # Set paths before initializing
    original_user_db = users.DB_PATH
    users.DB_PATH = str(db_path)
    users.init_db()

    yield

    # Restore original path
    users.DB_PATH = original_user_db


@pytest.fixture(scope="module", autouse=True)
def override_auth_for_validation_tests():
    """Override authentication only for file validation tests."""
    def override_get_current_user():
        return {"db_path": "test_db", "id": 1, "username": "testuser"}

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    # Clean up override after module tests complete
    app.dependency_overrides.clear()


client = TestClient(app)


@pytest.mark.parametrize("endpoint", ["/api/create-index/", "/api/update-index/"])
def test_reject_invalid_extension(endpoint):
    files = [("files", ("malware.exe", b"data"))]
    response = client.post(endpoint, data={"collection": "test"}, files=files)
    assert response.status_code == 400


@pytest.mark.parametrize("endpoint", ["/api/create-index/", "/api/update-index/"])
def test_reject_large_file(endpoint):
    original_limit = app_module.MAX_FILE_SIZE_MB
    app_module.MAX_FILE_SIZE_MB = 0
    try:
        files = [("files", ("doc.txt", b"a"))]
        response = client.post(endpoint, data={"collection": "test"}, files=files)
    finally:
        app_module.MAX_FILE_SIZE_MB = original_limit
    assert response.status_code == 400
