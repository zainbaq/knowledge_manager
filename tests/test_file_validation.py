import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import api.app as app_module
from api.app import app
from api.auth import get_current_user


def override_get_current_user():
    return {"db_path": "test_db"}


app.dependency_overrides[get_current_user] = override_get_current_user
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
