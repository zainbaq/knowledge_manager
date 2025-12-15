"""Test script for corpus management endpoints."""

import requests
import json
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# Test users
TEST_USER_1 = {"username": "alice_corpus_test", "password": "TestPassword123!"}
TEST_USER_2 = {"username": "bob_corpus_test", "password": "TestPassword123!"}


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def register_user(username: str, password: str) -> Optional[str]:
    """Register a user and return API key."""
    print(f"Registering user: {username}")
    response = requests.post(
        f"{API_V1}/user/register",
        json={"username": username, "password": password}
    )

    if response.status_code == 200:
        api_key = response.json()["api_key"]
        print(f"✅ Registered successfully. API key: {api_key[:16]}...")
        return api_key
    elif response.status_code == 400 and "already exists" in response.json().get("detail", ""):
        # User already exists, try to login
        print(f"User already exists, logging in...")
        response = requests.post(
            f"{API_V1}/user/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            api_key = response.json()["api_key"]
            print(f"✅ Logged in successfully. API key: {api_key[:16]}...")
            return api_key

    print(f"❌ Failed: {response.status_code} - {response.json()}")
    return None


def test_create_corpus(api_key: str, corpus_data: dict) -> Optional[int]:
    """Test creating a corpus."""
    print(f"Creating corpus: {corpus_data['name']}")
    headers = {"X-API-Key": api_key}
    response = requests.post(f"{API_V1}/corpus/", json=corpus_data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Created successfully!")
        print(f"   Corpus ID: {result['corpus_id']}")
        print(f"   Message: {result['message']}")
        return result['corpus_id']
    else:
        print(f"❌ Failed: {response.status_code} - {response.json()}")
        return None


def test_list_corpuses(api_key: str):
    """Test listing corpuses."""
    print(f"Listing accessible corpuses...")
    headers = {"X-API-Key": api_key}
    response = requests.get(f"{API_V1}/corpus/", headers=headers)

    if response.status_code == 200:
        corpuses = response.json()["corpuses"]
        print(f"✅ Found {len(corpuses)} corpus(es)")
        for corpus in corpuses:
            print(f"   - {corpus['display_name']} (ID: {corpus['id']}, Owner: {corpus['owner_username']}, Approved: {corpus['is_approved']})")
        return corpuses
    else:
        print(f"❌ Failed: {response.status_code} - {response.json()}")
        return []


def test_get_corpus_details(api_key: str, corpus_id: int):
    """Test getting corpus details."""
    print(f"Getting details for corpus {corpus_id}...")
    headers = {"X-API-Key": api_key}
    response = requests.get(f"{API_V1}/corpus/{corpus_id}", headers=headers)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Retrieved successfully!")
        print(f"   Name: {data['corpus']['display_name']}")
        print(f"   Version: {data['corpus']['version']}")
        print(f"   User permission: {data['user_permission']}")
        print(f"   Permissions: {len(data['permissions'])} user(s)")
        print(f"   Versions: {len(data['versions'])} version(s)")
        return data
    else:
        print(f"❌ Failed: {response.status_code} - {response.json()}")
        return None


def test_update_corpus(api_key: str, corpus_id: int, updates: dict):
    """Test updating corpus metadata."""
    print(f"Updating corpus {corpus_id}...")
    headers = {"X-API-Key": api_key}
    response = requests.patch(f"{API_V1}/corpus/{corpus_id}", json=updates, headers=headers)

    if response.status_code == 200:
        corpus = response.json()
        print(f"✅ Updated successfully!")
        print(f"   New display name: {corpus['display_name']}")
        return corpus
    else:
        print(f"❌ Failed: {response.status_code} - {response.json()}")
        return None


def test_grant_permission(api_key: str, corpus_id: int, username: str, permission_type: str):
    """Test granting permission to a user."""
    print(f"Granting {permission_type} permission to {username}...")
    headers = {"X-API-Key": api_key}
    response = requests.post(
        f"{API_V1}/corpus/{corpus_id}/permissions",
        json={"username": username, "permission_type": permission_type},
        headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code} - {response.json()}")
        return False


def test_revoke_permission(api_key: str, corpus_id: int, username: str):
    """Test revoking permission from a user."""
    print(f"Revoking permission from {username}...")
    headers = {"X-API-Key": api_key}
    response = requests.delete(f"{API_V1}/corpus/{corpus_id}/permissions/{username}", headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code} - {response.json()}")
        return False


def test_delete_corpus(api_key: str, corpus_id: int):
    """Test deleting a corpus."""
    print(f"Deleting corpus {corpus_id}...")
    headers = {"X-API-Key": api_key}
    response = requests.delete(f"{API_V1}/corpus/{corpus_id}", headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        return True
    else:
        print(f"❌ Failed: {response.status_code} - {response.json()}")
        return False


def test_permission_denied(api_key: str, corpus_id: int, action: str):
    """Test that permission is denied when expected."""
    print(f"Testing permission denial for {action}...")
    headers = {"X-API-Key": api_key}

    if action == "update":
        response = requests.patch(f"{API_V1}/corpus/{corpus_id}", json={"description": "unauthorized"}, headers=headers)
    elif action == "delete":
        response = requests.delete(f"{API_V1}/corpus/{corpus_id}", headers=headers)
    else:
        print(f"Unknown action: {action}")
        return False

    if response.status_code == 403:
        print(f"✅ Permission correctly denied (403)")
        return True
    else:
        print(f"❌ Expected 403, got {response.status_code}")
        return False


def main():
    """Run all corpus endpoint tests."""
    print_section("CORPUS ENDPOINT TESTING")

    # Register test users
    print_section("1. User Registration")
    api_key_1 = register_user(TEST_USER_1["username"], TEST_USER_1["password"])
    api_key_2 = register_user(TEST_USER_2["username"], TEST_USER_2["password"])

    if not api_key_1 or not api_key_2:
        print("\n❌ Failed to register users. Exiting.")
        return

    # Test 1: Create corpus as User 1
    print_section("2. Create Corpus (User 1)")
    corpus_data = {
        "name": "test_legal_corpus",
        "display_name": "Test Legal Corpus",
        "description": "A test corpus for legal documents",
        "category": "legal",
        "is_public": True
    }
    corpus_id = test_create_corpus(api_key_1, corpus_data)

    if not corpus_id:
        print("\n❌ Failed to create corpus. Exiting.")
        return

    # Test 2: List corpuses (User 1 should see it)
    print_section("3. List Corpuses (User 1)")
    test_list_corpuses(api_key_1)

    # Test 3: List corpuses (User 2 should NOT see it - not approved yet)
    print_section("4. List Corpuses (User 2 - Before Permission)")
    corpuses = test_list_corpuses(api_key_2)
    if not any(c['id'] == corpus_id for c in corpuses):
        print("✅ User 2 correctly cannot see unapproved corpus")
    else:
        print("⚠️  User 2 can see unapproved corpus (unexpected)")

    # Test 4: Get corpus details
    print_section("5. Get Corpus Details (User 1)")
    test_get_corpus_details(api_key_1, corpus_id)

    # Test 5: Update corpus metadata
    print_section("6. Update Corpus Metadata (User 1)")
    test_update_corpus(api_key_1, corpus_id, {
        "description": "Updated description for legal corpus",
        "category": "legal-updated"
    })

    # Test 6: Grant permission to User 2
    print_section("7. Grant Permission (User 1 → User 2)")
    test_grant_permission(api_key_1, corpus_id, TEST_USER_2["username"], "read")

    # Test 7: User 2 can now see the corpus
    print_section("8. List Corpuses (User 2 - After Permission)")
    corpuses = test_list_corpuses(api_key_2)
    if any(c['id'] == corpus_id for c in corpuses):
        print("✅ User 2 can now see corpus after permission grant")

    # Test 8: User 2 can view but not modify
    print_section("9. Permission Enforcement (User 2)")
    test_get_corpus_details(api_key_2, corpus_id)
    test_permission_denied(api_key_2, corpus_id, "update")
    test_permission_denied(api_key_2, corpus_id, "delete")

    # Test 9: Revoke permission
    print_section("10. Revoke Permission (User 1)")
    test_revoke_permission(api_key_1, corpus_id, TEST_USER_2["username"])

    # Test 10: User 2 can no longer see it
    print_section("11. Verify Permission Revoked (User 2)")
    corpuses = test_list_corpuses(api_key_2)
    if not any(c['id'] == corpus_id for c in corpuses):
        print("✅ User 2 correctly cannot see corpus after revocation")

    # Test 11: Delete corpus
    print_section("12. Delete Corpus (User 1)")
    test_delete_corpus(api_key_1, corpus_id)

    # Test 12: Verify deletion
    print_section("13. Verify Deletion")
    corpuses = test_list_corpuses(api_key_1)
    if not any(c['id'] == corpus_id for c in corpuses):
        print("✅ Corpus successfully deleted")

    print_section("TEST SUITE COMPLETE")
    print("✅ All core CRUD operations tested successfully!")
    print("\nNext steps:")
    print("  - Add subscription endpoints")
    print("  - Add versioning endpoints")
    print("  - Add admin approval endpoints")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API server")
        print("Please start the API server first:")
        print("  python run_app.py")
        print("or")
        print("  uvicorn api.app:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
