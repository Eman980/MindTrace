"""
test_duplicate_detection.py
---------------------------
Verification test suite for MindTrace duplicate lecture detection:
1. Upload a lecture for the first time -> creates new lecture.
2. Upload the exact same lecture again -> duplicate detected.
3. Upload the same lecture with a different filename -> duplicate detected.
4. Upload a different lecture with the same filename -> creates new lecture.
5. Open existing lecture after duplicate detection -> content and progress available.
6. Verify student progress and MCQ attempts are not reset.
"""

import sys
import os
import io
import hashlib

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from starlette.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.all_models import Lecture, Concept, Checkpoint, CheckpointAttempt

client = TestClient(app)

def run_tests():
    print("=" * 65)
    print("  MindTrace Duplicate Lecture Detection Test Suite")
    print("=" * 65)

    # 1. Login
    print("\n[Step 1] Authenticating Demo Student...")
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "demo@mindtrace.edu",
        "password": "mindtrace123"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   [OK] Authenticated successfully.")

    # Prepare unique test payloads
    # Distinct payload A
    content_a = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x04\x00\x00\x00TEST_A_AUDIO"
    hash_a = hashlib.sha256(content_a).hexdigest()
    
    # Distinct payload B
    content_b = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x04\x00\x00\x00TEST_B_AUDIO_DIFF"
    hash_b = hashlib.sha256(content_b).hexdigest()

    transcript_text = "This is a test lecture transcript about graph algorithms, depth first search and breadth first search traversal."

    db = SessionLocal()
    # Clean up test lectures if left over from a previous test run
    for h in [hash_a, hash_b]:
        existing = db.query(Lecture).filter(Lecture.file_hash == h).all()
        for l in existing:
            db.delete(l)
    db.commit()
    db.close()

    # -------------------------------------------------------------
    # Scenario 1: Upload a lecture for the first time -> New lecture created
    # -------------------------------------------------------------
    print("\n[Test 1] Uploading lecture file A for the first time...")
    file_stream_1 = io.BytesIO(content_a)
    resp1 = client.post(
        "/api/v1/lectures/upload",
        headers=headers,
        data={
            "title": "Graph Algorithms Lecture",
            "course_code": "CS301",
            "description": "Introduction to graph traversals.",
            "transcript_text": transcript_text
        },
        files={"file": ("lecture_graphs.wav", file_stream_1, "audio/wav")}
    )
    assert resp1.status_code == 200, f"Upload 1 failed: {resp1.text}"
    data1 = resp1.json()
    assert data1["is_duplicate"] is False, f"Expected is_duplicate=False, got {data1}"
    lec_id_1 = data1["lecture_id"]
    print(f"   [OK] Lecture 1 created with ID={lec_id_1}, is_duplicate={data1['is_duplicate']}")

    # -------------------------------------------------------------
    # Scenario 2: Upload the EXACT same lecture again -> Duplicate detected
    # -------------------------------------------------------------
    print("\n[Test 2] Uploading the exact same lecture file again...")
    file_stream_2 = io.BytesIO(content_a)
    resp2 = client.post(
        "/api/v1/lectures/upload",
        headers=headers,
        data={
            "title": "Graph Algorithms Lecture (Reupload)",
            "course_code": "CS301",
            "transcript_text": transcript_text
        },
        files={"file": ("lecture_graphs.wav", file_stream_2, "audio/wav")}
    )
    assert resp2.status_code == 200, f"Upload 2 failed: {resp2.text}"
    data2 = resp2.json()
    assert data2["is_duplicate"] is True, f"Expected is_duplicate=True, got {data2}"
    assert data2["lecture_id"] == lec_id_1, f"Expected duplicate to match ID={lec_id_1}, got {data2['lecture_id']}"
    assert "already exists in your library" in data2["message"], f"Expected duplicate message, got {data2['message']}"
    print(f"   [OK] Duplicate recognized! Matched existing lecture ID={data2['lecture_id']}")
    print(f"   [OK] Message returned: '{data2['message']}'")

    # -------------------------------------------------------------
    # Scenario 3: Upload same lecture with a DIFFERENT filename -> Duplicate detected
    # -------------------------------------------------------------
    print("\n[Test 3] Uploading the same lecture with a DIFFERENT filename ('renamed_graphs.wav')...")
    file_stream_3 = io.BytesIO(content_a)
    resp3 = client.post(
        "/api/v1/lectures/upload",
        headers=headers,
        data={
            "title": "Totally Different Title",
            "course_code": "CS301",
            "transcript_text": transcript_text
        },
        files={"file": ("renamed_graphs.wav", file_stream_3, "audio/wav")}
    )
    assert resp3.status_code == 200, f"Upload 3 failed: {resp3.text}"
    data3 = resp3.json()
    assert data3["is_duplicate"] is True, f"Expected is_duplicate=True on renamed file, got {data3}"
    assert data3["lecture_id"] == lec_id_1, f"Expected duplicate to match ID={lec_id_1}, got {data3['lecture_id']}"
    print(f"   [OK] Content hash recognized duplicate despite different filename! ID={data3['lecture_id']}")

    # -------------------------------------------------------------
    # Scenario 4: Upload a DIFFERENT lecture with the SAME filename -> New lecture created
    # -------------------------------------------------------------
    print("\n[Test 4] Uploading a genuinely DIFFERENT file with the SAME filename ('lecture_graphs.wav')...")
    file_stream_4 = io.BytesIO(content_b)  # Different content
    resp4 = client.post(
        "/api/v1/lectures/upload",
        headers=headers,
        data={
            "title": "Graph Algorithms Part 2",
            "course_code": "CS301",
            "transcript_text": "Different content discussing Dijkstra shortest path and Bellman-Ford algorithm."
        },
        files={"file": ("lecture_graphs.wav", file_stream_4, "audio/wav")}
    )
    assert resp4.status_code == 200, f"Upload 4 failed: {resp4.text}"
    data4 = resp4.json()
    assert data4["is_duplicate"] is False, f"Expected is_duplicate=False for different content, got {data4}"
    lec_id_4 = data4["lecture_id"]
    assert lec_id_4 != lec_id_1, f"Different lecture must have a new ID! Got {lec_id_4}"
    print(f"   [OK] Genuinely different content treated as brand new lecture! New ID={lec_id_4}")

    # -------------------------------------------------------------
    # Scenario 5 & 6: Verify existing lecture data, MCQs, and progress are NOT reset
    # -------------------------------------------------------------
    print("\n[Test 5 & 6] Verifying lecture details, checkpoints, and answer progress preservation...")
    detail_resp = client.get(f"/api/v1/lectures/{lec_id_1}", headers=headers)
    assert detail_resp.status_code == 200
    lecture_data = detail_resp.json()
    concepts = lecture_data.get("concepts", [])
    assert len(concepts) > 0, "Original lecture concepts missing"
    chk = concepts[0]["checkpoints"][0]
    
    # Submit an answer to checkpoint on lec_id_1
    opt = chk["options"][0] if chk.get("options") else "A"
    ans_resp = client.post("/api/v1/checkpoints/answer", headers=headers, json={
        "checkpoint_id": chk["id"],
        "student_answer": opt,
        "confidence_level": 3,
        "explanation_text": "First attempt before re-upload"
    })
    assert ans_resp.status_code == 200
    print(f"   [OK] Submitted checkpoint answer for Checkpoint ID={chk['id']}.")

    # Now simulate reuploading lecture A again
    file_stream_5 = io.BytesIO(content_a)
    resp5 = client.post(
        "/api/v1/lectures/upload",
        headers=headers,
        data={"title": "Graph Algorithms", "course_code": "CS301"},
        files={"file": ("lecture_graphs.wav", file_stream_5, "audio/wav")}
    )
    assert resp5.status_code == 200
    assert resp5.json()["is_duplicate"] is True

    # Check that previous answer and attempts on Checkpoint ID are still present
    verify_resp = client.get(f"/api/v1/lectures/{lec_id_1}", headers=headers)
    assert verify_resp.status_code == 200
    restored_concepts = verify_resp.json().get("concepts", [])
    restored_chk = restored_concepts[0]["checkpoints"][0]
    assert restored_chk["latest_attempt"] is not None, "Student checkpoint attempt was erroneously lost!"
    assert restored_chk["latest_attempt"]["student_answer"] == opt, "Student answer changed!"
    print(f"   [OK] Verified: MCQ attempts and student progress were completely preserved!")

    # -------------------------------------------------------------
    # Scenario 7: Database Unique Constraint & Integrity Verification
    # -------------------------------------------------------------
    print("\n[Test 7] Verifying database UNIQUE constraint on file_hash...")
    db = SessionLocal()
    count_lec1 = db.query(Lecture).filter(Lecture.file_hash == hash_a).count()
    assert count_lec1 == 1, f"Expected exactly 1 lecture row with hash_a, found {count_lec1}"
    print(f"   [OK] Verified exactly 1 database row for hash {hash_a[:16]}... (no duplicate rows created)")

    # -------------------------------------------------------------
    # Scenario 8: Simultaneous Concurrent Upload Simulation
    # -------------------------------------------------------------
    print("\n[Test 8] Simulating concurrent duplicate upload collision...")
    import concurrent.futures

    def do_upload(name_prefix):
        stream = io.BytesIO(content_a)
        r = client.post(
            "/api/v1/lectures/upload",
            headers=headers,
            data={"title": f"Concurrent {name_prefix}", "course_code": "CS301"},
            files={"file": (f"{name_prefix}.wav", stream, "audio/wav")}
        )
        return r.status_code, r.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futs = [executor.submit(do_upload, f"thread_{i}") for i in range(3)]
        results = [f.result() for f in futs]

    for status_code, json_res in results:
        assert status_code == 200, f"Concurrent request failed: {json_res}"
        assert json_res["is_duplicate"] is True
        assert json_res["lecture_id"] == lec_id_1
    print("   [OK] All concurrent upload attempts safely resolved to existing lecture ID without errors!")

    # Clean up test rows
    for h in [hash_a, hash_b]:
        for l in db.query(Lecture).filter(Lecture.file_hash == h).all():
            db.delete(l)
    db.commit()
    db.close()

    print("\n" + "=" * 65)
    print("  ALL DUPLICATE LECTURE DETECTION TESTS PASSED (100% SUCCESS)")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
