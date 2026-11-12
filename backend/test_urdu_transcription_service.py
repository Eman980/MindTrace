import unittest
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.transcription_service import transcription_service, COMPUTER_SCIENCE_PROMPT

class TestUrduTranscriptionService(unittest.TestCase):
    def test_01_cyrillic_hallucination_detection(self):
        """Verify that Cyrillic hallucinated noise triggers the quality warning."""
        bad_text = "1 wing one, 1ини unsettling system and more noise"
        warning = transcription_service.check_transcript_quality(bad_text, [])
        self.assertIsNotNone(warning)
        self.assertIn("unexpected foreign characters detected", warning)

    def test_02_short_audio_warning(self):
        """Verify that very short/silent audio triggers the quality warning."""
        short_text = "Hello world."
        warning = transcription_service.check_transcript_quality(short_text, [])
        self.assertIsNotNone(warning)
        self.assertIn("very short audio", warning)

    def test_03_clean_english_transcript_passes(self):
        """Verify that clean genuine computer science lecture text passes without warnings."""
        clean_text = (
            "In this lecture we explore recursive functions and how base cases prevent "
            "infinite stack frame growth. Every recursive call must move closer to the terminating condition."
        )
        warning = transcription_service.check_transcript_quality(clean_text, [{"text": clean_text}])
        self.assertIsNone(warning)

    def test_04_prompt_contains_relevant_keywords(self):
        """Verify prompt hint contains domain keywords to ground vocabulary."""
        self.assertIn("recursion", COMPUTER_SCIENCE_PROMPT.lower())
        self.assertIn("base cases", COMPUTER_SCIENCE_PROMPT.lower())
        self.assertIn("functions", COMPUTER_SCIENCE_PROMPT.lower())

if __name__ == "__main__":
    unittest.main()

