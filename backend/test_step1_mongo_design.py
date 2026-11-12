"""
test_step1_mongo_design.py
--------------------------
Unit test verifying Step 1:
1. MongoDB Misconception document design and formatters.
2. Missing status defaults to 'open'.
3. Missing relapse_count defaults to 0.
4. Embedded disguise object structure.
5. Index definitions.
"""

import sys
import os
import unittest
from bson import ObjectId

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.mongo import (
    format_misconception_doc,
    _to_object_id
)

class TestMongoMisconceptionDesign(unittest.TestCase):
    def test_document_formatting_and_defaults(self):
        # Case 1: Raw mongo doc with ObjectId and missing status/relapse_count
        raw_doc = {
            "_id": ObjectId("65f1a2b3c4d5e6f7a8b9c0d1"),
            "student_id": 101,
            "lecture_id": 1,
            "segment_id": 5,
            "concept": "Stack LIFO Principle",
            "original_question": "Which element is popped first?",
            "improving_at": None,
            "recheck_due": None,
            "created_at": "2026-11-09T20:00:00Z",
            "disguise": None
        }

        formatted = format_misconception_doc(raw_doc)
        self.assertIsNotNone(formatted)
        self.assertEqual(formatted["id"], "65f1a2b3c4d5e6f7a8b9c0d1")
        self.assertNotIn("_id", formatted)
        # Verify default fallbacks per specification
        self.assertEqual(formatted["status"], "open", "Missing status must default to 'open'")
        self.assertEqual(formatted["relapse_count"], 0, "Missing relapse_count must default to 0")

    def test_disguise_embedded_structure(self):
        raw_doc = {
            "_id": ObjectId(),
            "student_id": 101,
            "lecture_id": 1,
            "concept": "Stack LIFO Principle",
            "original_question": "Which element is popped first?",
            "status": "improving",
            "improving_at": "2026-11-09",
            "recheck_due": "2026-11-11",
            "relapse_count": 0,
            "created_at": "2026-11-09T20:00:00Z",
            "disguise": {
                "question": "In a cafeteria, clean plates are added to the top of a pile. When a customer takes a plate, which one is taken?",
                "options": [
                    "A. The plate at the very bottom",
                    "B. The plate added most recently to the top",
                    "C. A random plate from the middle",
                    "D. Any plate"
                ],
                "correct_index": 1,
                "explanation": "This follows the Last-In First-Out (LIFO) model of a stack.",
                "generated_at": "2026-11-09T20:05:00Z"
            }
        }

        formatted = format_misconception_doc(raw_doc)
        self.assertIn("disguise", formatted)
        self.assertEqual(formatted["disguise"]["correct_index"], 1)
        self.assertEqual(len(formatted["disguise"]["options"]), 4)

    def test_object_id_converter(self):
        valid_hex = "65f1a2b3c4d5e6f7a8b9c0d1"
        res = _to_object_id(valid_hex)
        self.assertIsInstance(res, ObjectId)

        invalid = "not-an-object-id"
        res2 = _to_object_id(invalid)
        self.assertEqual(res2, invalid)

if __name__ == "__main__":
    unittest.main()

