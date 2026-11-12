"""
app/services/disguise_service.py
--------------------------------
Generates context-shifted 'Disguise Test' MCQs using Groq openai/gpt-oss-20b.
Tests conceptual understanding instead of rote memory.
"""

import json
import httpx
import datetime
from typing import Dict, Any, List
from app.config import settings

async def generate_disguise_mcq(concept: str, original_question: str) -> Dict[str, Any]:
    """
    Calls Groq with model openai/gpt-oss-20b to generate 1 MCQ testing
    the same concept in a completely different scenario.
    """
    if settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}",
            "Content-Type": "application/json"
        }
        prompt = (
            f"You are an expert computer science professor designing a diagnostic Disguise Test.\n"
            f"Concept: '{concept}'\n"
            f"Original question student saw: '{original_question}'\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Create ONE completely new Multiple Choice Question testing the exact same invariant/principle of '{concept}', "
            f"but in a completely different real-world context/story (e.g., cafeteria trays, cafeteria line, warehouse dispatch, library shelves, etc.).\n"
            f"2. Do NOT reuse the original wording, example numbers, or keywords.\n"
            f"3. Ensure the question tests true conceptual transfer, so a student who memorized keywords will not pass by rote.\n"
            f"4. Provide exactly 4 options (prefixed with A., B., C., D.).\n"
            f"5. Set correct_index as an integer between 0 and 3.\n"
            f"6. Return strictly a JSON object with this exact format (no markdown formatting, no code fences):\n"
            f'{{\n  "question": "...",\n  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],\n  "correct_index": 0,\n  "explanation": "..."\n}}'
        )
        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "system", "content": "You are a specialized diagnostic question generator. Return strictly raw JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    raw_content = resp.json()["choices"][0]["message"]["content"].strip()
                    # Strip markdown code fences if present
                    if raw_content.startswith("```json"):
                        raw_content = raw_content[7:]
                    elif raw_content.startswith("```"):
                        raw_content = raw_content[3:]
                    if raw_content.endswith("```"):
                        raw_content = raw_content[:-3]
                    parsed = json.loads(raw_content.strip())
                    if "question" in parsed and "options" in parsed and len(parsed["options"]) == 4 and "correct_index" in parsed:
                        parsed["generated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        return parsed
        except Exception as e:
            print(f"[DisguiseService] Groq API warning: {e}")

    # Deterministic fallback question for local/offline testing
    return {
        "question": f"In a novel real-world scenario applying the principle of '{concept}', an observer analyzes how elements are ordered and retrieved. Which option correctly demonstrates this principle?",
        "options": [
            f"A. The sequence strictly enforces the core invariant of '{concept}'.",
            "B. The elements are discarded randomly without maintaining sequence.",
            "C. All items are simultaneously available in arbitrary order.",
            "D. The operation terminates immediately without state changes."
        ],
        "correct_index": 0,
        "explanation": f"This question verifies the conceptual invariant of {concept} in an unfamiliar context.",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

