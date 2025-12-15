import requests
import time
import sys

API_URL = "http://localhost:8000"

def test_performance():
    print("=" * 60)
    print("Phase 2 Performance Test")
    print("=" * 60)
    
    # 1. Register and get API key
    print("\n1. Registering test user...")
    try:
        register_response = requests.post(
            f"{API_URL}/api/user/register",
            json={"username": "perftest", "password": "PerfTest123!"}
        )
        if register_response.status_code != 200:
            print(f"   Registration failed (user may already exist): {register_response.status_code}")
            # Try login instead
            login_response = requests.post(
                f"{API_URL}/api/user/login",
                json={"username": "perftest", "password": "PerfTest123!"}
            )
            api_key = login_response.json()["api_key"]
        else:
            api_key = register_response.json()["api_key"]
        print(f"   ✓ Got API key: {api_key[:10]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        print("   Make sure the API is running: python run_app.py")
        sys.exit(1)
    
    headers = {"X-API-Key": api_key}
    
    # 2. Test parallel embedding generation
    print("\n2. Testing parallel embedding generation...")
    print("   Creating document with ~20 chunks...")
    
    # Create a document that will produce multiple chunks
    large_content = "Machine learning is transforming technology. " * 200
    
    with open("test_large_doc.txt", "w") as f:
        f.write(large_content)
    
    start = time.time()
    with open("test_large_doc.txt", "rb") as f:
        upload_response = requests.post(
            f"{API_URL}/api/create-index/",
            data={"collection": "perf_test_1"},
            files={"files": ("large_doc.txt", f, "text/plain")},
            headers=headers
        )
    upload_time = time.time() - start
    
    if upload_response.status_code == 200:
        chunks = upload_response.json()["indexed_chunks"]
        print(f"   ✓ Uploaded {chunks} chunks in {upload_time:.2f}s")
        print(f"   → Time per chunk: {upload_time/chunks:.2f}s")
        print(f"   → Expected with parallelization: <3s total for 20 chunks")
    else:
        print(f"   ✗ Upload failed: {upload_response.text}")
    
    # 3. Create multiple collections for multi-query test
    print("\n3. Creating multiple collections...")
    for i in range(2, 6):
        content = f"Collection {i} contains information about topic {i}. " * 50
        with open(f"test_doc_{i}.txt", "w") as f:
            f.write(content)
        
        with open(f"test_doc_{i}.txt", "rb") as f:
            requests.post(
                f"{API_URL}/api/create-index/",
                data={"collection": f"perf_test_{i}"},
                files={"files": (f"doc{i}.txt", f, "text/plain")},
                headers=headers
            )
        print(f"   ✓ Created perf_test_{i}")
    
    # 4. Test parallel multi-collection query
    print("\n4. Testing parallel multi-collection query...")
    print("   Querying 5 collections...")
    
    start = time.time()
    query_response = requests.post(
        f"{API_URL}/api/query/",
        json={"query": "What is machine learning?"},  # Query all collections
        headers=headers
    )
    query_time = time.time() - start
    
    if query_response.status_code == 200:
        context_len = len(query_response.json()["context"])
        print(f"   ✓ Queried 5 collections in {query_time:.2f}s")
        print(f"   → Context length: {context_len} chars")
        print(f"   → Expected with parallelization: <1s for 5 collections")
    else:
        print(f"   ✗ Query failed: {query_response.text}")
    
    # 5. Cleanup
    print("\n5. Cleaning up test collections...")
    for i in range(1, 6):
        requests.delete(
            f"{API_URL}/api/delete-index/perf_test_{i}",
            headers=headers
        )
    print("   ✓ Cleanup complete")
    
    # Summary
    print("\n" + "=" * 60)
    print("Performance Summary")
    print("=" * 60)
    print(f"Upload (parallel embeddings): {upload_time:.2f}s for {chunks} chunks")
    print(f"Query (parallel collections): {query_time:.2f}s for 5 collections")
    print("\nExpected improvements from Phase 2:")
    print("  • Embedding generation: 10-20x faster")
    print("  • Multi-collection query: 4-5x faster")
    print("=" * 60)

if __name__ == "__main__":
    test_performance()
