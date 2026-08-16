"""Tests for the corpus management endpoints and the corpus RBAC layer.

These drive api/corpus_auth.py through the HTTP surface in api/v1/corpus.py,
which is how its ownership and permission-hierarchy checks are actually reached.

There is no moderation/approval step: a corpus's own is_public flag is the
single source of truth for visibility, set directly by its owner. is_approved
is always kept equal to is_public by the API layer (see api/v1/corpus.py) and
is not exercised as an independent axis here.
"""

import pytest

from api import corpus_db
from vector_store import vector_index


CORPUS_PAYLOAD = {
    "name": "legal_corpus",
    "display_name": "Legal Corpus",
    "description": "A corpus of legal documents",
    "category": "legal",
    "is_public": True,
}


@pytest.fixture(autouse=True)
def corpus_test_env(test_db, tmp_path, monkeypatch):
    """Point the corpus tables and the vector store at per-test temp locations.

    conftest's test_db only repoints api.users.DB_PATH. api.corpus_db keeps its
    own module-level DB_PATH, and vector_store.vector_index binds VECTOR_DB_PATH
    at import time, so without these two a corpus row and its on-disk directory
    land in the developer's real database instead of the temp one.
    """
    monkeypatch.setattr(corpus_db, "DB_PATH", str(test_db))
    monkeypatch.setattr(vector_index, "VECTOR_DB_PATH", str(tmp_path / "vectors"))
    yield


@pytest.fixture
def other_key(register_api_user):
    """API key for a second user, so permission checks have someone to deny."""
    return register_api_user("bob")


def auth(api_key: str) -> dict:
    return {"X-API-Key": api_key}


def create_corpus(client, api_key: str, **overrides) -> int:
    """Create a corpus and return its ID."""
    payload = {**CORPUS_PAYLOAD, **overrides}
    response = client.post("/api/v1/corpus/", json=payload, headers=auth(api_key))
    assert response.status_code == 200, response.text
    return response.json()["corpus_id"]


def grant(client, api_key: str, corpus_id: int, username: str, permission: str):
    return client.post(
        f"/api/v1/corpus/{corpus_id}/permissions",
        json={"username": username, "permission_type": permission},
        headers=auth(api_key),
    )


def corpus_ids(client, api_key: str) -> set:
    response = client.get("/api/v1/corpus/", headers=auth(api_key))
    assert response.status_code == 200, response.text
    return {corpus["id"] for corpus in response.json()["corpuses"]}


# --- Create ---------------------------------------------------------------


def test_create_corpus_returns_id_and_is_immediately_public(client, api_key):
    """There is no moderation step: is_approved mirrors is_public on creation."""
    response = client.post("/api/v1/corpus/", json=CORPUS_PAYLOAD, headers=auth(api_key))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["corpus_id"] >= 1
    assert body["corpus_name"] == "legal_corpus"

    detail = client.get(f"/api/v1/corpus/{body['corpus_id']}", headers=auth(api_key))
    assert detail.json()["corpus"]["is_approved"] is True


def test_create_private_corpus_is_not_approved_either(client, api_key):
    """is_approved mirrors is_public in both directions, not just when public."""
    corpus_id = create_corpus(client, api_key, is_public=False)

    detail = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(api_key))
    assert detail.json()["corpus"]["is_approved"] is False


def test_create_corpus_rejects_duplicate_name(client, api_key):
    create_corpus(client, api_key)

    response = client.post("/api/v1/corpus/", json=CORPUS_PAYLOAD, headers=auth(api_key))

    assert response.status_code == 409, response.text


def test_corpus_endpoints_reject_unauthenticated_requests(client):
    assert client.post("/api/v1/corpus/", json=CORPUS_PAYLOAD).status_code == 401
    assert client.get("/api/v1/corpus/").status_code == 401


# --- List -----------------------------------------------------------------


def test_list_corpuses_returns_own_corpus(client, api_key):
    corpus_id = create_corpus(client, api_key)

    response = client.get("/api/v1/corpus/", headers=auth(api_key))

    assert response.status_code == 200, response.text
    corpuses = response.json()["corpuses"]
    assert [c["id"] for c in corpuses] == [corpus_id]
    assert corpuses[0]["owner_username"] == "alice"
    assert corpuses[0]["display_name"] == "Legal Corpus"


def test_list_corpuses_hides_another_users_private_corpus(client, api_key, other_key):
    corpus_id = create_corpus(client, api_key, is_public=False)

    assert corpus_id not in corpus_ids(client, other_key)


def test_list_corpuses_includes_public_corpus_immediately(client, api_key, other_key):
    """Public corpuses need no separate approval to become visible."""
    corpus_id = create_corpus(client, api_key)

    assert corpus_id in corpus_ids(client, other_key)


# --- Get details ----------------------------------------------------------


def test_get_corpus_details_reports_owner_permission_and_initial_version(client, api_key):
    corpus_id = create_corpus(client, api_key)

    response = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(api_key))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["corpus"]["id"] == corpus_id
    assert body["user_permission"] == "owner"
    assert [(p["username"], p["permission_type"]) for p in body["permissions"]] == [
        ("alice", "owner")
    ]
    assert [v["version"] for v in body["versions"]] == [1]


def test_get_unknown_corpus_returns_404(client, api_key):
    response = client.get("/api/v1/corpus/999", headers=auth(api_key))

    assert response.status_code == 404, response.text


def test_stranger_cannot_read_a_private_corpus(client, api_key, other_key):
    corpus_id = create_corpus(client, api_key, is_public=False)

    response = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(other_key))

    assert response.status_code == 403, response.text


def test_public_corpus_is_readable_without_an_explicit_grant(client, api_key, other_key):
    corpus_id = create_corpus(client, api_key)

    response = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(other_key))

    assert response.status_code == 200, response.text
    assert response.json()["user_permission"] is None


# --- Update ---------------------------------------------------------------


def test_update_corpus_metadata_as_owner(client, api_key):
    corpus_id = create_corpus(client, api_key)

    response = client.patch(
        f"/api/v1/corpus/{corpus_id}",
        json={"display_name": "Renamed Corpus", "description": "Updated", "category": "law"},
        headers=auth(api_key),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["display_name"] == "Renamed Corpus"
    assert body["description"] == "Updated"
    assert body["category"] == "law"

    persisted = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(api_key)).json()
    assert persisted["corpus"]["display_name"] == "Renamed Corpus"


# --- Grant / revoke permission --------------------------------------------


def test_grant_read_permission_makes_corpus_visible_and_readable(client, api_key, other_key):
    corpus_id = create_corpus(client, api_key, is_public=False)

    response = grant(client, api_key, corpus_id, "bob", "read")

    assert response.status_code == 200, response.text
    assert response.json()["permission_type"] == "read"
    assert corpus_id in corpus_ids(client, other_key)

    detail = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(other_key))
    assert detail.status_code == 200, detail.text
    assert detail.json()["user_permission"] == "read"


def test_grant_permission_overwrites_an_existing_grant(client, api_key, other_key):
    corpus_id = create_corpus(client, api_key, is_public=False)

    assert grant(client, api_key, corpus_id, "bob", "read").status_code == 200
    assert grant(client, api_key, corpus_id, "bob", "admin").status_code == 200

    detail = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(other_key)).json()
    assert detail["user_permission"] == "admin"
    assert sum(1 for p in detail["permissions"] if p["username"] == "bob") == 1


def test_grant_permission_to_unknown_user_returns_404(client, api_key):
    corpus_id = create_corpus(client, api_key)

    response = grant(client, api_key, corpus_id, "nobody", "read")

    assert response.status_code == 404, response.text


def test_revoke_permission_removes_access(client, api_key, other_key):
    corpus_id = create_corpus(client, api_key, is_public=False)
    assert grant(client, api_key, corpus_id, "bob", "read").status_code == 200

    response = client.delete(
        f"/api/v1/corpus/{corpus_id}/permissions/bob", headers=auth(api_key)
    )

    assert response.status_code == 200, response.text
    assert corpus_id not in corpus_ids(client, other_key)
    denied = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(other_key))
    assert denied.status_code == 403, denied.text


def test_cannot_revoke_the_owners_permission(client, api_key):
    corpus_id = create_corpus(client, api_key)

    response = client.delete(
        f"/api/v1/corpus/{corpus_id}/permissions/alice", headers=auth(api_key)
    )

    assert response.status_code == 400, response.text


# --- Delete ---------------------------------------------------------------


def test_delete_corpus_as_owner(client, api_key):
    corpus_id = create_corpus(client, api_key)

    response = client.delete(f"/api/v1/corpus/{corpus_id}", headers=auth(api_key))

    assert response.status_code == 200, response.text
    assert corpus_ids(client, api_key) == set()
    assert client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(api_key)).status_code == 404


# --- Versions -------------------------------------------------------------


def test_list_versions_returns_the_version_created_with_the_corpus(client, api_key):
    corpus_id = create_corpus(client, api_key)

    response = client.get(f"/api/v1/corpus/{corpus_id}/versions", headers=auth(api_key))

    assert response.status_code == 200, response.text
    versions = response.json()
    assert [v["version"] for v in versions] == [1]
    assert versions[0]["created_by"] == "alice"
    assert versions[0]["chunk_count"] == 0
    assert versions[0]["file_count"] == 0


def test_create_version_increments_and_records_the_creator(client, api_key):
    corpus_id = create_corpus(client, api_key)

    response = client.post(
        f"/api/v1/corpus/{corpus_id}/versions",
        json={"description": "Added Q1 documents"},
        headers=auth(api_key),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 2
    assert body["description"] == "Added Q1 documents"
    assert body["created_by"] == "alice"

    detail = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(api_key)).json()
    assert detail["corpus"]["version"] == 2


def test_created_version_is_listed_ahead_of_the_original(client, api_key):
    corpus_id = create_corpus(client, api_key)
    assert (
        client.post(
            f"/api/v1/corpus/{corpus_id}/versions",
            json={"description": "second"},
            headers=auth(api_key),
        ).status_code
        == 200
    )

    response = client.get(f"/api/v1/corpus/{corpus_id}/versions", headers=auth(api_key))

    assert response.status_code == 200, response.text
    versions = response.json()
    assert [v["version"] for v in versions] == [2, 1]
    assert versions[0]["description"] == "second"


def test_version_endpoints_agree_with_corpus_detail_on_field_names(client, api_key):
    """All three call sites build CorpusVersionInfo; they must agree on its shape."""
    corpus_id = create_corpus(client, api_key)

    created = client.post(
        f"/api/v1/corpus/{corpus_id}/versions",
        json={"description": "snapshot"},
        headers=auth(api_key),
    )
    assert created.status_code == 200, created.text
    listed = client.get(f"/api/v1/corpus/{corpus_id}/versions", headers=auth(api_key))
    assert listed.status_code == 200, listed.text
    detail = client.get(f"/api/v1/corpus/{corpus_id}", headers=auth(api_key))
    assert detail.status_code == 200, detail.text

    from_create = created.json()
    from_list = next(v for v in listed.json() if v["version"] == 2)
    from_detail = next(v for v in detail.json()["versions"] if v["version"] == 2)

    assert from_create.keys() == from_list.keys() == from_detail.keys()
    assert from_list == from_detail
    assert from_create["created_by"] == from_list["created_by"] == "alice"


def test_below_admin_permission_cannot_create_a_version(client, api_key, other_key):
    corpus_id = create_corpus(client, api_key, is_public=False)
    assert grant(client, api_key, corpus_id, "bob", "write").status_code == 200

    response = client.post(
        f"/api/v1/corpus/{corpus_id}/versions",
        json={"description": "unauthorized"},
        headers=auth(other_key),
    )

    assert response.status_code == 403, response.text


def test_stranger_cannot_list_versions_of_a_private_corpus(client, api_key, other_key):
    corpus_id = create_corpus(client, api_key, is_public=False)

    response = client.get(f"/api/v1/corpus/{corpus_id}/versions", headers=auth(other_key))

    assert response.status_code == 403, response.text


# --- Permission hierarchy: owner > admin > write > read -------------------


@pytest.mark.parametrize("permission", ["read", "write", "admin"])
def test_granted_permissions_never_allow_deleting_a_corpus(
    client, api_key, other_key, permission
):
    """Delete requires "owner", which grant_permission cannot hand out."""
    corpus_id = create_corpus(client, api_key, is_public=False)
    assert grant(client, api_key, corpus_id, "bob", permission).status_code == 200

    response = client.delete(f"/api/v1/corpus/{corpus_id}", headers=auth(other_key))

    assert response.status_code == 403, response.text


@pytest.mark.parametrize("permission", ["read", "write"])
def test_below_admin_permission_cannot_update_or_share(
    client, api_key, other_key, permission
):
    corpus_id = create_corpus(client, api_key, is_public=False)
    assert grant(client, api_key, corpus_id, "bob", permission).status_code == 200

    update = client.patch(
        f"/api/v1/corpus/{corpus_id}",
        json={"description": "unauthorized"},
        headers=auth(other_key),
    )
    assert update.status_code == 403, update.text

    assert grant(client, other_key, corpus_id, "bob", "admin").status_code == 403


def test_admin_permission_can_update_and_share(
    client, api_key, other_key, register_api_user
):
    corpus_id = create_corpus(client, api_key, is_public=False)
    assert grant(client, api_key, corpus_id, "bob", "admin").status_code == 200
    carol_key = register_api_user("carol")

    update = client.patch(
        f"/api/v1/corpus/{corpus_id}",
        json={"description": "edited by an admin"},
        headers=auth(other_key),
    )

    assert update.status_code == 200, update.text
    assert update.json()["description"] == "edited by an admin"
    assert grant(client, other_key, corpus_id, "carol", "read").status_code == 200
    assert corpus_id in corpus_ids(client, carol_key)


def test_stranger_cannot_update_or_delete_a_public_corpus(client, api_key, other_key):
    """is_public only shortcuts the read tier - update/delete still need admin/owner."""
    corpus_id = create_corpus(client, api_key)

    update = client.patch(
        f"/api/v1/corpus/{corpus_id}",
        json={"description": "unauthorized"},
        headers=auth(other_key),
    )
    assert update.status_code == 403, update.text

    delete = client.delete(f"/api/v1/corpus/{corpus_id}", headers=auth(other_key))
    assert delete.status_code == 403, delete.text
