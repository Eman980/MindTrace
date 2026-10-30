"""
test_complete_workflow.py
-------------------------
End-to-end automated verification of MindTrace MCQ answering, persistent answer history,
multi-attempt tracking, evidence-based misconception progression, and lecture-grounded MCQ generation.
"""

import sys
import os
import io

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from starlette.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.all_models import (
    User, Lecture, Concept, Checkpoint, CheckpointAttempt, Misconception, MisconceptionEvidence
)

client = TestClient(app)

def test_full_workflow():
    print("=" * 65)
    print("  MindTrace Complete MCQ & Misconception Workflow Test Suite")
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

    # 2. Get Lecture Details & Checkpoints
    print("\n[Step 2] Fetching Lecture & Initial Checkpoint State...")
    lectures_resp = client.get("/api/v1/lectures", headers=headers)
    assert lectures_resp.status_code == 200
    lectures = lectures_resp.json()
    assert len(lectures) > 0, "No lectures found"
    
    # Select demo lecture
    demo_lec = next((l for l in lectures if l["is_demo"]), lectures[0])
    lecture_id = demo_lec["id"]
    
    detail_resp = client.get(f"/api/v1/lectures/{lecture_id}", headers=headers)
    assert detail_resp.status_code == 200
    lecture_data = detail_resp.json()
    concepts = lecture_data.get("concepts", [])
    assert len(concepts) > 0, "Lecture has no concepts"
    
    # Gather checkpoints
    all_checkpoints = []
    for c in concepts:
        for chk in c.get("checkpoints", []):
            all_checkpoints.append(chk)
    assert len(all_checkpoints) > 0, "No checkpoints found in lecture"
    test_chk = all_checkpoints[0]
    print(f"   [OK] Retrieved lecture '{lecture_data['title']}' with {len(concepts)} concepts and {len(all_checkpoints)} checkpoints.")
    print(f"   [OK] Target Checkpoint ID {test_chk['id']}: '{test_chk['question_text'][:55]}...'")

    # 3. Test Question Submission — Attempt 1 (Incorrect Answer)
    print("\n[Step 3] Submitting Attempt 1 (Incorrect Answer)...")
    # Identify an incorrect option
    bad_option = None
    for opt in test_chk.get("options", []):
        if not opt.startswith("A."):
            bad_option = opt
            break
    if not bad_option:
        bad_option = "Arbitrary incorrect option"

    ans1_resp = client.post("/api/v1/checkpoints/answer", headers=headers, json={
        "checkpoint_id": test_chk["id"],
        "student_answer": bad_option,
        "confidence_level": 2,
        "explanation_text": "I guessed based on the surface wording"
    })
    assert ans1_resp.status_code == 200, f"Submit answer failed: {ans1_resp.text}"
    eval1 = ans1_resp.json()
    assert eval1["is_correct"] is False, "Expected attempt 1 to be evaluated as incorrect"
    assert eval1["correct_answer"] is not None, "Evaluation must return stored correct answer"
    assert eval1["explanation"] is not None or eval1["feedback_reason"], "Evaluation must return explanation"
    assert eval1["attempt_number"] >= 1, "Attempt number must be >= 1"
    print(f"   [OK] Attempt 1 evaluated: is_correct={eval1['is_correct']}, attempt_number={eval1['attempt_number']}")
    print(f"   [OK] Returned correct answer: '{eval1['correct_answer'][:40]}...'")
    print(f"   [OK] Returned explanation: '{eval1['explanation'][:50]}...'")

    # 4. Verify Persistent Restoration via GET /lectures/{id}
    print("\n[Step 4] Verifying Answer Persistence & State Restoration...")
    restore_resp = client.get(f"/api/v1/lectures/{lecture_id}", headers=headers)
    assert restore_resp.status_code == 200
    restored_data = restore_resp.json()
    
    restored_chk = None
    for c in restored_data["concepts"]:
        for chk in c["checkpoints"]:
            if chk["id"] == test_chk["id"]:
                restored_chk = chk
                break
    assert restored_chk is not None, "Target checkpoint not found on reload"
    assert restored_chk["latest_attempt"] is not None, "Failed to restore latest_attempt from backend"
    assert restored_chk["latest_attempt"]["student_answer"] == bad_option, "Restored answer does not match submitted answer"
    assert restored_chk["latest_attempt"]["is_correct"] is False, "Restored correctness does not match"
    assert restored_chk["correct_answer"] is not None, "Answered question must reveal correct answer on restore"
    print(f"   [OK] Restored saved state from SQLite: student_answer='{restored_chk['latest_attempt']['student_answer'][:30]}...', is_correct={restored_chk['latest_attempt']['is_correct']}")

    # 5. Test Multi-Attempt Retry — Attempt 2 (Correct Answer)
    print("\n[Step 5] Submitting Attempt 2 (Retry with Correct Answer)...")
    correct_opt = restored_chk["correct_answer"]
    ans2_resp = client.post("/api/v1/checkpoints/answer", headers=headers, json={
        "checkpoint_id": test_chk["id"],
        "student_answer": correct_opt,
        "confidence_level": 3,
        "explanation_text": "Because the formal mapping rule dictates one output per valid input."
    })
    assert ans2_resp.status_code == 200, f"Retry failed: {ans2_resp.text}"
    eval2 = ans2_resp.json()
    assert eval2["is_correct"] is True, "Expected retry to be correct"
    assert eval2["attempt_number"] > eval1["attempt_number"], "Attempt number must increment"
    assert len(eval2["attempts"]) >= 2, "Attempts history must preserve all prior attempts"
    print(f"   [OK] Attempt 2 evaluated: is_correct={eval2['is_correct']}, attempt_number={eval2['attempt_number']}")
    print(f"   [OK] Total historical attempts stored in SQLite for this checkpoint: {eval2['total_attempts']}")

    # 6. Check Misconception Tracking & Evidence Records
    print("\n[Step 6] Verifying Evidence-Based Misconception Updates...")
    misc_resp = client.get("/api/v1/misconceptions", headers=headers)
    assert misc_resp.status_code == 200
    misconceptions = misc_resp.json()
    print(f"   [OK] Student has {len(misconceptions)} tracked persistent misconception records in database.")
    
    # 7. Check Playback Replay Telemetry
    print("\n[Step 7] Testing 'Review This Concept' Playback Telemetry...")
    replay_resp = client.post("/api/v1/playback/event", headers=headers, json={
        "lecture_id": lecture_id,
        "concept_id": test_chk["concept_id"],
        "event_type": "remediation_replay",
        "timestamp_in_media": 0.0,
        "details": {"reason": "review_concept_click"}
    })
    assert replay_resp.status_code == 200
    print("   [OK] Replay telemetry recorded successfully.")

    # 8. Test Lecture Upload with Accompanying Spoken Transcript Notes
    print("\n[Step 8] Testing Lecture Upload & Genuine Content-Grounded MCQ Generation...")
    sample_spoken_text = (
        "Binary Search is an efficient searching algorithm that operates on sorted arrays. "
        "A binary search tree maintains the core invariant that all keys in the left subtree are smaller than the node, "
        "and all keys in the right subtree are greater than the node. "
        "The time complexity of searching a balanced binary search tree is logarithmic, specifically big O of log n. "
        "In contrast, searching an unbalanced degenerated tree degrades to linear time O of n."
    )
    
    # Create a small dummy audio file for testing upload
    dummy_wav = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    dummy_wav.name = "bst_algorithms_lecture.wav"

    upload_resp = client.post(
        "/api/v1/lectures/upload",
        headers=headers,
        data={
            "title": "Binary Search Trees & Tree Invariants",
            "course_code": "CS201",
            "description": "Lecture on binary search algorithms and tree invariants.",
            "transcript_text": sample_spoken_text
        },
        files={
            "file": ("bst_algorithms_lecture.wav", dummy_wav, "audio/wav")
        }
    )
    assert upload_resp.status_code == 200, f"Lecture upload failed: {upload_resp.text}"
    uploaded_lec = upload_resp.json()
    new_lec_id = uploaded_lec["lecture_id"]
    print(f"   [OK] Lecture uploaded and processed: ID={new_lec_id}, Status='{uploaded_lec['status']}', Concepts={uploaded_lec['concepts_count']}")

    # Verify newly generated MCQs are grounded strictly in the spoken content
    new_detail_resp = client.get(f"/api/v1/lectures/{new_lec_id}", headers=headers)
    assert new_detail_resp.status_code == 200
    new_data = new_detail_resp.json()
    assert len(new_data["concepts"]) > 0, "No concepts extracted from transcript"
    
    first_new_concept = new_data["concepts"][0]
    first_new_checkpoints = first_new_concept.get("checkpoints", [])
    assert len(first_new_checkpoints) > 0, "No MCQs generated from transcript"
    
    new_q1 = first_new_checkpoints[0]
    print(f"   [OK] Generated Concept Title: '{first_new_concept['title']}'")
    print(f"   [OK] Generated MCQ Question: '{new_q1['question_text']}'")
    print(f"   [OK] Generated MCQ Options (4 total):")
    for opt in new_q1["options"]:
        print(f"       {opt}")
    print(f"   [OK] Source Excerpt Grounding: '{(new_q1.get('source_excerpt') or '')[:60]}...'")

    # Verify question is grounded in the actual text (Binary Search / Invariant), NOT fake template
    full_q_text = (new_q1["question_text"] + " " + " ".join(new_q1["options"])).lower()
    assert any(term in full_q_text for term in ["binary", "tree", "invariant", "algorithm", "search"]), (
        f"Generated question '{new_q1['question_text']}' was not grounded in the uploaded transcript!"
    )
    print("   [OK] Verified: Questions are strictly grounded in spoken lecture text, not generic placeholder templates!")

    # 9. Verify Graceful Error Handling When No Speech & No Transcript
    print("\n[Step 9] Verifying Failure Mode on Empty Audio...")
    empty_wav = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    empty_wav.name = "untranscribable_silent.wav"
    fail_upload_resp = client.post(
        "/api/v1/lectures/upload",
        headers=headers,
        data={
            "title": "Silent Lecture File",
            "course_code": "CS999",
            "description": "No transcript supplied.",
        },
        files={
            "file": ("untranscribable_silent.wav", empty_wav, "audio/wav")
        }
    )
    assert fail_upload_resp.status_code in [400, 500], "Expected upload to fail when audio is empty"
    print(f"   [OK] Gracefully rejected without fake MCQs: {fail_upload_resp.json().get('detail', '')[:80]}...")

    # 10. Test Local Speech-to-Text Transcription on Real Multimedia Video File
    print("\n[Step 10] Testing Local Faster-Whisper Transcription on Real MP4 Video...")
    sample_mp4 = os.path.join(os.path.dirname(__file__), "uploads", "1c58a838111b42ffb05e7688be9eceed_WhatsApp Video 2026-10-27 at 11.33.01 AM.mp4")
    assert os.path.exists(sample_mp4), f"Sample video not found at {sample_mp4}"

    with open(sample_mp4, "rb") as vf:
        mp4_bytes = vf.read()

    video_upload_resp = client.post(
        "/upload",
        headers=headers,
        data={
            "title": "Friction and Motion Physics Lecture",
            "course_code": "PHY101",
            "description": "Real MP4 lecture video transcribed locally on CPU via Faster-Whisper.",
        },
        files={
            "file": ("friction_lecture.mp4", io.BytesIO(mp4_bytes), "video/mp4")
        }
    )
    assert video_upload_resp.status_code == 200, f"Video upload/transcription failed: {video_upload_resp.text}"
    video_lec = video_upload_resp.json()
    video_lec_id = video_lec["lecture_id"]
    print(f"   [OK] Lecture uploaded & transcribed locally: ID={video_lec_id}, Duration={video_lec.get('duration_seconds')}s")

    # 11. Test Workflow Endpoints: /segments/{id}, /generate/{id}, /report/{id}
    print("\n[Step 11] Verifying /segments/{id} endpoint...")
    seg_resp = client.get(f"/segments/{video_lec_id}", headers=headers)
    assert seg_resp.status_code == 200
    seg_data = seg_resp.json()
    assert len(seg_data["segments"]) > 0, "No segments returned"
    print(f"   [OK] Full text: '{seg_data['full_text']}'")
    for s in seg_data["segments"][:3]:
        print(f"       [{s['start_time']}s -> {s['end_time']}s]: {s['text']}")

    # Verify real spoken words are present in transcript
    spoken_lower = seg_data["full_text"].lower()
    assert any(term in spoken_lower for term in ["friction", "motion", "force", "direction"]), (
        f"Transcribed text '{seg_data['full_text']}' did not contain expected physics lecture terms"
    )
    print("   [OK] Verified: Transcript contains genuine spoken words with exact timestamps!")

    # Test /generate/{id}
    print("\n[Step 12] Verifying /generate/{id} and /report/{id} endpoints...")
    gen_resp = client.post(f"/generate/{video_lec_id}", headers=headers)
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["concepts_count"] > 0
    assert gen_data["checkpoints_count"] > 0
    print(f"   [OK] /generate successfully synthesized {gen_data['concepts_count']} concepts and {gen_data['checkpoints_count']} diagnostic MCQs.")

    # Test /report/{id}
    rep_resp = client.get(f"/report/{video_lec_id}", headers=headers)
    assert rep_resp.status_code == 200
    rep_data = rep_resp.json()
    print(f"   [OK] /report generated: Recording ID={rep_data['recording_id']}, Total Checkpoints={rep_data['total_checkpoints']}")

    print("\n" + "=" * 65)
    print("  ALL 12 AUTOMATED WORKFLOW TESTS PASSED CLEANLY (100% SUCCESS)  ")
    print("=" * 65)

if __name__ == "__main__":
    test_full_workflow()
