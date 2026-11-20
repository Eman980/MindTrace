"""
explanation_check_service.py
-----------------------------
LLM-based explanation checker for evidence-based misconception resolution.

When a student answers an MCQ correctly and writes a one-line "why",
this service judges whether the explanation is valid, too brief, or flawed.
It is NOT a hard gate.

VERDICTS
  valid                – correct reasoning; counts as a pass.
  too_brief            – too short/vague to judge; no pass, follow-up needed.
  flawed_matches_label – reasoning matches a known misconception label; no pass.
  flawed_other         – clearly wrong reasoning, no label match; no pass.
  not_checked          – no AI key, or the AI call failed.

DESIGN RULES (per brief)
- A "flawed" verdict alone must NEVER set memorized_flag.
- Raw LLM output is stored for the false-positive audit.

AI PROVIDER
- Groq is used first (same as the rest of MindTrace).
- OpenAI is used only if no Groq key is configured.
"""

import json
import re
import httpx
from typing import Optional
from app.config import settings


# ── Verdict constants ────────────────────────────────────────────────────────
VERDICT_VALID = "valid"
VERDICT_TOO_BRIEF = "too_brief"
VERDICT_FLAWED_LABEL = "flawed_matches_label"
VERDICT_FLAWED_OTHER = "flawed_other"
VERDICT_NOT_CHECKED = "not_checked"

VERDICTS_THAT_COUNT_AS_PASS = {VERDICT_VALID}
VERDICTS_THAT_NEED_FOLLOWUP = {VERDICT_TOO_BRIEF, VERDICT_FLAWED_LABEL, VERDICT_FLAWED_OTHER}

# ── AI provider settings ─────────────────────────────────────────────────────
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GROQ_MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
OPENAI_MODELS = ["gpt-4o-mini"]


class ExplanationCheckService:
    """Judges a student's one-line explanation using Groq (OpenAI only as fallback)."""

    def __init__(self):
        self.groq_key = (getattr(settings, "GROQ_API_KEY", "") or "").strip()
        self.openai_key = (getattr(settings, "OPENAI_API_KEY", "") or "").strip()

    async def check(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        explanation_text: str,
        concept_title: str,
        known_misconception_labels: Optional[list[str]] = None,
    ) -> dict:
        """
        Returns
        -------
        {
            "verdict": str,             # one of the verdicts above
            "verdict_reason": str,      # one sentence for the UI
            "matched_label": str|None,  # only for flawed_matches_label
            "raw_llm_output": str,      # raw AI text (for audit)
            "llm_used": bool,           # False if no AI was used
        }
        """
        # Guard: missing or very short explanation -> too_brief
        if not explanation_text or len(explanation_text.strip()) < 8:
            return {
                "verdict": VERDICT_TOO_BRIEF,
                "verdict_reason": "Explanation was missing or too short to evaluate.",
                "matched_label": None,
                "raw_llm_output": "{}",
                "llm_used": False,
            }

        # Try the AI path
        if self.groq_key or self.openai_key:
            try:
                return await self._check_with_llm(
                    question_text,
                    correct_answer,
                    student_answer,
                    explanation_text,
                    concept_title,
                    known_misconception_labels or [],
                )
            except Exception as exc:
                print(f"[ExplanationCheckService] LLM call failed: {exc}. Returning not_checked.")

        # Fallback: no key or AI error
        return {
            "verdict": VERDICT_NOT_CHECKED,
            "verdict_reason": "Explanation check skipped (no API key or service error).",
            "matched_label": None,
            "raw_llm_output": "{}",
            "llm_used": False,
        }

    async def _check_with_llm(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        explanation_text: str,
        concept_title: str,
        known_labels: list[str],
    ) -> dict:
        # Groq first; OpenAI only if there is no Groq key
        if self.groq_key:
            url, key, models = GROQ_URL, self.groq_key, GROQ_MODELS
        else:
            url, key, models = OPENAI_URL, self.openai_key, OPENAI_MODELS

        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        labels_block = ""
        if known_labels:
            labels_block = (
                "\nKnown misconception labels for this concept:\n"
                + "\n".join(f"  - {lbl}" for lbl in known_labels)
            )

        prompt = f"""You are an educational assessment specialist evaluating whether a student's explanation demonstrates genuine understanding or rote memorization.

CONTEXT
Concept: {concept_title}
Question: {question_text}
Correct answer: {correct_answer}
Student selected: {student_answer}  <- this is correct
Student's one-line explanation (written BEFORE seeing feedback): "{explanation_text}"{labels_block}

TASK
Evaluate the explanation and return a JSON object with exactly these keys:

verdict         (string, EXACTLY one of: "valid", "too_brief", "flawed_matches_label", "flawed_other")
verdict_reason  (string, 1 sentence for the student, encouraging but honest)
matched_label   (string or null - the specific misconception label if verdict is "flawed_matches_label", else null)

VERDICT DEFINITIONS
- "valid"                : The explanation shows correct reasoning aligned with the concept. Small wording imprecision is fine.
- "too_brief"            : Too vague or too short to judge understanding (e.g. "because it's right" or "I just knew").
- "flawed_matches_label" : The answer is correct but the reason given reveals a known misconception from the list above.
- "flawed_other"         : The answer is correct but the reason is clearly wrong or contradicts the concept, and doesn't match a known label.

IMPORTANT RULES
- Be lenient: a student can be correct for a slightly imprecise reason. Only flag "flawed" when reasoning is clearly wrong.
- Never invent misconception labels; only use one from the provided list for "flawed_matches_label".
- Output only valid JSON, no markdown fences."""

        raw, parsed, last_error = "", {}, None

        async with httpx.AsyncClient(timeout=30.0) as client:
            for model in models:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a strict but fair educational AI. Output only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1200,
                }
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    raw = resp.json()["choices"][0]["message"]["content"] or ""
                    parsed = self._parse_json(raw)
                    if parsed:
                        break
                    last_error = ValueError("AI returned no JSON")
                except Exception as exc:
                    last_error = exc

        if not parsed:
            raise last_error or RuntimeError("No AI response")

        verdict = parsed.get("verdict", VERDICT_NOT_CHECKED)
        # Reject unexpected verdict strings
        if verdict not in {VERDICT_VALID, VERDICT_TOO_BRIEF, VERDICT_FLAWED_LABEL, VERDICT_FLAWED_OTHER}:
            verdict = VERDICT_NOT_CHECKED

        return {
            "verdict": verdict,
            "verdict_reason": str(parsed.get("verdict_reason", "")),
            "matched_label": parsed.get("matched_label") or None,
            "raw_llm_output": raw,
            "llm_used": True,
        }

    @staticmethod
    def _parse_json(raw: str) -> dict:
        """Removes markdown fences and extracts the first JSON object."""
        text = re.sub(r"```(?:json)?", "", raw or "").strip()
        match = re.search(r"\{[\s\S]*\}", text)
        return json.loads(match.group()) if match else {}


# ── State machine helpers (unchanged) ─────────────────────────────────────────

def compute_evidence_status(
    current_status: Optional[str],
    wrong_evidence_count: int,
    confidence_level: Optional[int],
) -> str:
    """
    Applies the Suspected -> Confirmed transition on a WRONG answer.

    Rules (from brief):
      Suspected : first wrong answer mapped to a label.
      Confirmed : two or more wrong evidences on different items,
                  OR one wrong answer with confidence == 3.
    """
    if current_status in ("Resolved", "Recurred"):
        # Any new wrong answer after Resolved -> Recurred
        return "Recurred"

    if wrong_evidence_count >= 2 or confidence_level == 3:
        return "Confirmed"

    return "Suspected"


def should_count_as_pass(
    is_correct: bool,
    verdict: str,
    confidence_level: Optional[int],
    confidence_floor: int,
) -> bool:
    """
    True only if this attempt counts toward the N_PASS tally:
      - must be correct
      - explanation verdict must be "valid"
      - confidence_level must be >= confidence_floor
    """
    if not is_correct:
        return False
    if verdict != VERDICT_VALID:
        return False
    if confidence_level is None or confidence_level < confidence_floor:
        return False
    return True


def evaluate_resolution(
    n_passing_attempts: int,
    has_delayed_pass: bool,
    intervention_shown: bool,
    n_pass_threshold: int,
) -> bool:
    """
    True if ALL resolution criteria are satisfied:
      1. Intervention was shown to the student.
      2. At least N_PASS valid passes on reworded/transfer items.
      3. At least one pass was MIN_DELAY_HOURS after the intervention.
    """
    return (
        intervention_shown
        and n_passing_attempts >= n_pass_threshold
        and has_delayed_pass
    )


explanation_check_service = ExplanationCheckService()