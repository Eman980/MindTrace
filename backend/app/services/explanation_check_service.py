"""
explanation_check_service.py
-----------------------------
LLM-based explanation checker for evidence-based misconception resolution.

PURPOSE
-------
When a student answers correctly and provides a one-line "why" explanation,
this service judges whether the explanation is genuinely valid or potentially
rote/flawed — without using it as a hard gate (per the FYP brief).

VERDICTS (4 graduated levels)
------------------------------
  valid               – Explanation demonstrates correct reasoning; counts as
                        a pass toward resolution if other criteria are met.
  too_brief           – Explanation is too short / vague to judge; does NOT
                        count as a pass. A variant/transfer follow-up is
                        scheduled.
  flawed_matches_label – Explanation contains reasoning that matches a known
                        misconception label for this concept; does NOT count
                        as a pass. Schedules a follow-up.
  flawed_other        – Explanation is clearly wrong but doesn't map to a
                        specific catalog label; does NOT count as a pass.

IMPORTANT DESIGN DECISIONS (per brief)
---------------------------------------
- A "flawed" verdict alone MUST NEVER set memorized_flag.
  memorized_flag is set only if the student then fails a follow-up variant/
  transfer item after the explanation was flagged as flawed.
- Every verdict stores raw LLM output for E2 (false-positive rate audit).
- If no OpenAI key is configured, or if the LLM call fails, the verdict
  defaults to "not_checked" and the attempt is still recorded cleanly.
"""

import json
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


class ExplanationCheckService:
    """Calls GPT-4o-mini to evaluate a student's one-line explanation."""

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY

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
        Parameters
        ----------
        question_text           : The MCQ question stem.
        correct_answer          : The correct answer option.
        student_answer          : What the student picked (should be correct,
                                  since we only check explanations on correct
                                  answers).
        explanation_text        : The student's one-line "why" before feedback.
        concept_title           : Concept name, for context.
        known_misconception_labels : Optional list of catalog labels for this
                                  concept (used to detect flawed_matches_label).

        Returns
        -------
        {
            "verdict": str,          # one of the four verdicts above
            "verdict_reason": str,   # one-sentence explanation for the UI
            "matched_label": str|None,  # if flawed_matches_label, which one
            "raw_llm_output": str,   # full JSON string from LLM (for audit)
            "llm_used": bool,        # False if fell back to rule-based
        }
        """
        # ── Guard: no explanation or very short → too_brief immediately ─────
        if not explanation_text or len(explanation_text.strip()) < 8:
            return {
                "verdict": VERDICT_TOO_BRIEF,
                "verdict_reason": "Explanation was missing or too short to evaluate.",
                "matched_label": None,
                "raw_llm_output": "{}",
                "llm_used": False,
            }

        # ── Try LLM path ─────────────────────────────────────────────────────
        if self.api_key:
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

        # ── Fallback: not_checked (no key or LLM error) ───────────────────────
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
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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
Student selected: {student_answer}  ← this is correct
Student's one-line explanation (written BEFORE seeing feedback): "{explanation_text}"{labels_block}

TASK
Evaluate the explanation and return a JSON object with exactly these keys:

verdict         (string, EXACTLY one of: "valid", "too_brief", "flawed_matches_label", "flawed_other")
verdict_reason  (string, 1 sentence for the student, encouraging but honest)
matched_label   (string or null — the specific misconception label if verdict is "flawed_matches_label", else null)

VERDICT DEFINITIONS
- "valid"                : The explanation shows correct reasoning aligned with the concept. Small wording imprecision is fine.
- "too_brief"            : Too vague or too short to judge understanding (e.g. "because it's right" or "I just knew").
- "flawed_matches_label" : The answer is correct but the reason given reveals a known misconception from the list above.
- "flawed_other"         : The answer is correct but the reason is clearly wrong or contradicts the concept, and doesn't match a known label.

IMPORTANT RULES
- Be lenient: a student can be correct for a slightly imprecise reason. Only flag "flawed" when reasoning is clearly wrong.
- Never invent misconception labels; only use one from the provided list for "flawed_matches_label".
- Output only valid JSON, no markdown fences."""

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a strict but fair educational AI. Output only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()

        raw = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(raw)

        verdict = parsed.get("verdict", VERDICT_NOT_CHECKED)
        # Sanitize: reject unexpected verdict strings
        if verdict not in {VERDICT_VALID, VERDICT_TOO_BRIEF, VERDICT_FLAWED_LABEL, VERDICT_FLAWED_OTHER}:
            verdict = VERDICT_NOT_CHECKED

        return {
            "verdict": verdict,
            "verdict_reason": str(parsed.get("verdict_reason", "")),
            "matched_label": parsed.get("matched_label") or None,
            "raw_llm_output": raw,
            "llm_used": True,
        }


# ── State machine helpers ─────────────────────────────────────────────────────

def compute_evidence_status(
    current_status: Optional[str],
    wrong_evidence_count: int,
    confidence_level: Optional[int],
) -> str:
    """
    Applies the Suspected → Confirmed transition on a WRONG answer.

    Rules (from brief):
      Suspected : first wrong answer mapped to a label.
      Confirmed : two or more wrong evidences on different items,
                  OR one wrong answer with confidence == 3.

    Parameters
    ----------
    current_status      : existing evidence_status (may be None for new row)
    wrong_evidence_count: total wrong evidences accumulated INCLUDING this one
    confidence_level    : student-reported confidence on THIS attempt (1|2|3)

    Returns new evidence_status string.
    """
    if current_status in ("Resolved", "Recurred"):
        # Any new wrong answer after Resolved → Recurred
        return "Recurred"

    # Confirmed if: ≥2 wrong evidences OR single wrong with confidence=3
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
    Returns True only if this attempt should count toward the N_PASS tally
    for resolution.

    Rules:
      - must be correct
      - explanation_verdict must be "valid"
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
    Returns True if ALL resolution criteria are satisfied.

    Criteria (ALL must hold):
      1. Intervention was shown to the student.
      2. At least N_PASS correct answers on reworded/transfer items
         (never the same original), each with verdict=valid and
         confidence >= CONFIDENCE_FLOOR.
      3. At least one of those passes was at least MIN_DELAY_HOURS
         after the intervention.
    """
    return (
        intervention_shown
        and n_passing_attempts >= n_pass_threshold
        and has_delayed_pass
    )


explanation_check_service = ExplanationCheckService()
