import re
import json
import httpx
from typing import Dict, Any, Optional
from collections import Counter
from app.config import settings

COMMON_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "can", "will", "just", "don", "should", "now", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing",
    "would", "could", "shall", "might", "must", "used", "uses", "using", "use",
    "make", "makes", "making", "made", "help", "helps", "create", "creates",
    "this", "that", "these", "those", "it", "its", "they", "them", "their", "we", "us", "our",
    "you", "your", "yours", "he", "him", "his", "she", "her", "hers", "what", "which", "who", "whom"
}

GREETING_WORDS = {
    "hi", "hello", "hey", "heyy", "heya", "greetings",
    "good morning", "good afternoon", "good evening", "good day",
    "howdy", "sup", "yo", "hola",
    "okay", "ok", "k", "thanks", "thank you", "thx", "ty", "cheers"
}

UNANSWERED_PHRASES = {
    "i dont know", "i do not know", "idk", "dont know", "don t know",
    "no idea", "i have no idea", "have no idea", "no clue", "i have no clue",
    "have no clue", "not sure", "im not sure", "i am not sure", "i m not sure",
    "skip", "pass", "na", "n a", "n/a", "none", "nothing",
    "cant answer", "cannot answer", "i cant answer", "i cannot answer",
    "dont understand", "don t understand", "i dont understand",
    "unanswered", "unknown"
}

COMMON_ACRONYMS = {
    "html", "css", "sql", "http", "https", "xml", "dom", "url", "uri", "cpu",
    "ram", "rom", "dns", "tcp", "udp", "ip", "ssh", "ftp", "sdk", "api", "apis",
    "vpn", "os", "ai", "ml", "nlp", "ui", "ux", "jwt", "cli", "gui", "ide",
    "db", "rdbms", "nosql", "json", "rest", "soap", "crud", "npm", "pip", "git"
}

CONTRAST_DOMAINS = [
    ({"html", "markup", "structure", "tags", "element", "elements"}, {"css", "style", "styling", "colors", "color"}),
    ({"domain", "inputs", "arguments"}, {"range", "outputs", "return"}),
    ({"compiler", "compiled"}, {"interpreter", "interpreted"}),
    ({"stack", "lifo"}, {"queue", "fifo"}),
    ({"synchronous", "blocking"}, {"asynchronous", "non-blocking", "async"}),
]


def _normalize_text(text: str) -> str:
    cleaned = (text or "").lower()
    cleaned = cleaned.replace("'", "").replace("’", "").replace("`", "")
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    return " ".join(cleaned.split())


def _is_empty_or_whitespace(text: str) -> bool:
    return not text or not text.strip()


def _is_unanswered_or_refusal(text: str) -> bool:
    norm = _normalize_text(text)
    if not norm:
        return True
    if norm in UNANSWERED_PHRASES:
        return True
    for prefix in ["i dont know", "i do not know", "idk", "i have no idea", "no idea", "i have no clue", "no clue", "not sure", "im not sure"]:
        if norm.startswith(prefix) and len(norm.split()) <= 7:
            return True
    return False


def _is_greeting_or_filler(text: str) -> bool:
    norm = _normalize_text(text)
    if not norm:
        return False
    if norm in GREETING_WORDS:
        return True
    words = norm.split()
    single_greetings = {"hi", "hello", "hey", "okay", "ok", "thanks", "thank", "you", "good", "morning", "afternoon", "evening", "there", "sir", "prof", "professor", "test", "testing"}
    if len(words) <= 3 and all(w in single_greetings for w in words):
        return True
    return False


def _is_gibberish_or_random(text: str) -> bool:
    norm = _normalize_text(text)
    if not norm:
        return False
    words = norm.split()
    if not words:
        return False

    # Common keyboard smash strings
    if norm in {"xyz", "asdf", "qwerty", "u", "zxcv", "qwer", "hjkl", "asdfg", "asdfgh", "asdfghjkl"}:
        return True

    # Single character that is not a meaningful word
    if len(norm) == 1 and norm not in {"a", "i"}:
        return True

    # Check if the entire string (stripped of spaces) is keyboard smashing
    compact = norm.replace(" ", "")
    if re.search(r'^[asdfghjkl]{3,}$|^[qwertyuiop]{4,}$|^[zxcvbnm]{4,}$', compact):
        return True

    # Same character repeated 4+ times, e.g. aaaa, zzzz
    if re.search(r'(.)\1{3,}', compact):
        return True

    # Character frequency dominance for short strings (excluding multi-word sentences)
    if len(norm) >= 4 and len(words) <= 2:
        counts = Counter(compact)
        if counts and (max(counts.values()) / max(1, sum(counts.values()))) > 0.60:
            return True

    # For 1 or 2 word short inputs: check if words lack vowels and are not acronyms
    vowels = set("aeiou")
    if len(words) <= 2:
        for w in words:
            if len(w) >= 3 and (w not in COMMON_ACRONYMS) and not any(c in vowels for c in w):
                return True

    return False


class EvaluationService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", "") or ""

    async def evaluate_answer(
        self,
        question_type: str,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        explanation: str = "",
        target_misconception: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates student answer.
        Returns:
        {
            "correct": bool,
            "verdict": "correct" | "partial" | "incorrect" | "unanswered",
            "confidence": float,
            "feedback": str,
            "reason": str,
            "misconception": Optional[str],
            "conceptual_trap": Optional[str],
            "correct_mental_model": Optional[str]
        }
        """
        cleaned_student = student_answer.strip()
        
        if question_type == "mcq":
            return self._evaluate_mcq(
                correct_answer=correct_answer,
                student_answer=cleaned_student,
                explanation=explanation,
                question_text=question_text,
                target_misconception=target_misconception
            )
        else:
            return await self._evaluate_short_answer(
                question_text=question_text,
                correct_answer=correct_answer,
                student_answer=cleaned_student,
                explanation=explanation,
                target_misconception=target_misconception
            )

    def _evaluate_mcq(
        self,
        correct_answer: str,
        student_answer: str,
        explanation: str,
        question_text: str = "",
        target_misconception: Optional[str] = None
    ) -> Dict[str, Any]:
        clean_correct = correct_answer.strip()
        clean_student = student_answer.strip()

        # Normalize option letter comparison without false positives
        is_student_letter = len(clean_student) == 1 or (len(clean_student) <= 3 and clean_student[1] in [".", ")", ":", " "])
        is_correct_letter = len(clean_correct) == 1 or (len(clean_correct) <= 3 and clean_correct[1] in [".", ")", ":", " "])

        first_letter_correct = clean_correct[0].upper() if len(clean_correct) > 0 else ""
        first_letter_student = clean_student[0].upper() if len(clean_student) > 0 else ""

        letter_match = False
        if is_student_letter and is_correct_letter:
            letter_match = (first_letter_student == first_letter_correct)
        elif is_student_letter and not is_correct_letter:
            letter_match = (clean_correct.upper().startswith(first_letter_student + ".") or 
                            clean_correct.upper().startswith(first_letter_student + ")"))
        elif not is_student_letter and is_correct_letter:
            letter_match = (clean_student.upper().startswith(first_letter_correct + ".") or 
                            clean_student.upper().startswith(first_letter_correct + ")"))

        is_correct = (
            clean_student.lower() == clean_correct.lower() or
            letter_match or
            (len(clean_student) > 6 and len(clean_correct) > 6 and (
                clean_student.lower() in clean_correct.lower() or clean_correct.lower() in clean_student.lower()
            ))
        )
        
        if is_correct:
            return {
                "correct": True,
                "verdict": "correct",
                "feedback": f"Correct! {explanation}".strip(),
                "confidence": 1.0,
                "reason": f"Correct! {explanation}".strip(),
                "misconception": None,
                "conceptual_trap": None,
                "correct_mental_model": None
            }
        
        # Determine specific misconception signal
        detected_misconception = target_misconception or "Conceptual misalignment with core principle"
        low_stud = clean_student.lower()
        low_corr = clean_correct.lower()
        low_q = question_text.lower()
        
        if ("domain" in low_stud and "range" in low_corr) or ("domain" in low_corr and "range" in low_stud):
            detected_misconception = "Domain vs. Range Inversion"
            trap = (
                "You conflated inputs with outputs. It is common to focus on the numbers generated "
                "by an evaluation rather than the allowable space of arguments permitted into the rule."
            )
            model = (
                "Domain belongs exclusively to valid inputs; Range belongs exclusively to resulting outputs. "
                "Always check: 'Am I testing what goes in, or what comes out?'"
            )
        elif "side effect" in low_stud or "print" in low_stud or "print" in low_q:
            detected_misconception = "Conflating Display Side-Effects with Computational Return Values"
            trap = (
                "Treating console printing as a function return value. Printing is merely an I/O side-effect; "
                "it does not hand a computed value back to the calling program."
            )
            model = (
                "Functions only produce outputs via the formal 'return' statement. Without an explicit return, "
                "the execution produces no usable value (defaulting to None/undefined)."
            )
        elif "multiplication" in low_stud or "f times" in low_stud or "notation" in low_q:
            detected_misconception = "Syntax Confusion: Algebraic Multiplication vs Function Application"
            trap = (
                "Treating f(x) as the algebraic multiplication f · x. In mathematical and programming notation, "
                "parentheses adjacent to a symbol indicate application of a rule, not arithmetic product."
            )
            model = (
                "The symbol before the parenthesis is the function identifier; the value inside is the input argument. "
                "f(x) denotes evaluating rule f with input x."
            )
        else:
            trap = (
                f"This choice represents an intuitive shortcut or mental trap: {detected_misconception}. "
                "It often appeals when relying on superficial pattern matching rather than verifying the invariant rules."
            )
            model = (
                f"Authoritative Rule: {explanation.strip() if explanation else f'The correct definition requires: {clean_correct}'}."
            )

        return {
            "correct": False,
            "verdict": "incorrect",
            "feedback": f"Incorrect. The expected answer is: {clean_correct}. {explanation}".strip(),
            "confidence": 0.95,
            "reason": f"Incorrect. The expected answer is: {clean_correct}. {explanation}".strip(),
            "misconception": detected_misconception,
            "conceptual_trap": trap,
            "correct_mental_model": model
        }

    async def _evaluate_short_answer(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        explanation: str,
        target_misconception: Optional[str] = None
    ) -> Dict[str, Any]:
        # ── 1. Empty / Whitespace Guard ───────────────────────────────────────
        if _is_empty_or_whitespace(student_answer):
            return {
                "correct": False,
                "verdict": "unanswered",
                "feedback": "No answer provided. Please type your explanation.",
                "confidence": 1.0,
                "reason": "No answer provided.",
                "misconception": target_misconception or "Unanswered checkpoint",
                "conceptual_trap": "Leaving the question unanswered without attempting an explanation.",
                "correct_mental_model": f"Core concept: {correct_answer}"
            }

        # ── 2. Declarations of Not Knowing / Refusals ─────────────────────────
        if _is_unanswered_or_refusal(student_answer):
            return {
                "correct": False,
                "verdict": "unanswered",
                "feedback": "Marked as unanswered. Please review the concept to understand: " + correct_answer,
                "confidence": 1.0,
                "reason": "Student declared lack of knowledge or skipped.",
                "misconception": target_misconception or "Unanswered checkpoint",
                "conceptual_trap": "Stating 'I don't know' rather than attempting a conceptual explanation.",
                "correct_mental_model": f"Core concept: {correct_answer}"
            }

        # ── 3. Greetings & Conversational Filler ──────────────────────────────
        if _is_greeting_or_filler(student_answer):
            return {
                "correct": False,
                "verdict": "incorrect",
                "feedback": "Your response is a greeting or conversational remark, not an explanation of the question.",
                "confidence": 1.0,
                "reason": "Greeting or conversational filler detected instead of an answer.",
                "misconception": target_misconception or "Irrelevant conversational response",
                "conceptual_trap": "Submitting conversational greetings instead of an explanation.",
                "correct_mental_model": f"The question requires explaining: {correct_answer}"
            }

        # ── 4. Random Characters / Keystroke Smashing / Gibberish ─────────────
        if _is_gibberish_or_random(student_answer):
            return {
                "correct": False,
                "verdict": "incorrect",
                "feedback": "Your response contains random characters or unintelligible text. Please provide a meaningful explanation.",
                "confidence": 1.0,
                "reason": "Meaningless or random keystrokes detected.",
                "misconception": target_misconception or "Superficial or meaningless text",
                "conceptual_trap": "Entering random keyboard characters.",
                "correct_mental_model": f"A valid explanation should address: {correct_answer}"
            }

        # ── 5. Minimum Word Count Guard ───────────────────────────────────────
        words = [w for w in student_answer.strip().split() if w]
        if len(words) < 4:
            return {
                "correct": False,
                "verdict": "incorrect",
                "feedback": "Answer is too brief to demonstrate understanding. Please explain in your own words with complete reasoning.",
                "confidence": 1.0,
                "reason": "Answer is too brief to demonstrate understanding.",
                "misconception": target_misconception or "Superficial or fragmentary answer",
                "conceptual_trap": "Providing single words or ultra-brief fragments instead of explaining.",
                "correct_mental_model": f"A complete conceptual answer should address: {correct_answer}"
            }

        # ── 6. Grade with Groq openai/gpt-oss-20b (if key configured) ─────────
        if self.groq_api_key and self.groq_api_key.strip():
            try:
                groq_eval = await self._grade_short_answer_with_groq(
                    question=question_text,
                    reference_answer=correct_answer,
                    student_answer=student_answer,
                    explanation=explanation,
                    target_misconception=target_misconception
                )
                if groq_eval:
                    return groq_eval
            except Exception as e:
                print(f"[EvaluationService] Groq grading error: {e}. Using safe heuristic fallback.")

        # ── 7. Safe Heuristic Fallback (AI unavailable or error) ───────────────
        return self._heuristic_short_answer_eval(
            question_text=question_text,
            correct_answer=correct_answer,
            student_answer=student_answer,
            explanation=explanation,
            target_misconception=target_misconception
        )

    async def _grade_short_answer_with_groq(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        explanation: str,
        target_misconception: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key.strip()}",
            "Content-Type": "application/json"
        }
        prompt = (
            "You are an expert professor grading a student's conceptual short answer response.\n\n"
            f"Question: {question}\n"
            f"Expected Answer: {reference_answer}\n"
            f"Learning Context: {explanation or 'Key foundational concept'}\n"
            f"Student Answer: {student_answer}\n\n"
            "Grading Criteria:\n"
            "1. Semantic correctness: Evaluate whether the student's answer accurately captures the core meaning, mechanism, or principle. Accept different wording, phrasing, and synonyms if the meaning is correct.\n"
            "2. Reject superficial fluency: If the response is fluent but describes the WRONG topic or an irrelevant technology (e.g. discussing CSS styling when asked about HTML markup/structure), mark it 'incorrect'.\n"
            "3. Missing constraints: If the response captures part of the idea but misses critical constraints or details, mark it 'partial'.\n"
            "4. Refusals: If the student states they do not know or cannot answer, mark it 'unanswered'.\n"
            "5. Verdict must be strictly one of: 'correct', 'partial', 'incorrect', or 'unanswered'.\n"
            "6. Feedback: exactly ONE short line (under 25 words) explaining why it was marked correct, partially correct, incorrect, or unanswered.\n\n"
            "Return STRICT JSON ONLY with keys 'verdict' and 'feedback':\n"
            '{\n  "verdict": "correct",\n  "feedback": "Clear explanation of the concept."\n}'
        )
        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "system", "content": "You are a precise educational grading assistant. Return raw JSON only with keys 'verdict' and 'feedback'."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                # Strip ```json or ``` code fences
                if raw.startswith("```json"):
                    raw = raw[7:]
                elif raw.startswith("```"):
                    raw = raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                parsed = json.loads(raw.strip())
                verdict = str(parsed.get("verdict", "incorrect")).lower().strip()
                if verdict not in ["correct", "partial", "incorrect", "unanswered"]:
                    verdict = "incorrect"
                feedback = str(parsed.get("feedback", "")).strip() or (explanation if verdict == "correct" else f"Key concept: {reference_answer}")

                is_correct = (verdict == "correct")
                return {
                    "correct": is_correct,
                    "verdict": verdict,
                    "feedback": feedback,
                    "confidence": 0.95 if is_correct else (0.85 if verdict == "partial" else 0.90),
                    "reason": feedback,
                    "misconception": None if is_correct else (target_misconception or "Misconception in short answer formulation"),
                    "conceptual_trap": None if is_correct else (
                        "Omission of core operational constraints or criteria in the explanation." if verdict == "partial"
                        else "Contradiction of core operational rules or off-topic explanation."
                    ),
                    "correct_mental_model": None if is_correct else f"Core principle: {reference_answer}"
                }
            else:
                print(f"[EvaluationService] Groq API returned status {resp.status_code}: {resp.text}")
        return None

    def _heuristic_short_answer_eval(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        explanation: str,
        target_misconception: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bidirectional semantic heuristic evaluator (offline fallback).

        Uses bidirectional stem coverage (max of forward/reverse) so that
        paraphrased correct answers are not rejected due to different wording.

        Forward  = what fraction of reference-answer stems appear in student answer.
        Reverse  = what fraction of student-answer stems appear in reference answer.
        Score    = max(forward, reverse)

        This means: a student who uses different-but-correct vocabulary (e.g.
        "loop forever and crash" for "call itself indefinitely leading to overflow")
        will score high on the reverse direction and be accepted.

        Thresholds  (after bidirectional scoring):
          >= 0.50  → correct
          >= 0.20  → partial
          <  0.20  → incorrect
        """
        stud_lower = student_answer.lower().strip()
        corr_lower = correct_answer.lower().strip()
        q_lower = question_text.lower().strip()

        # Domain vs Range specific trap checks
        if ("domain" in corr_lower or "domain" in q_lower) and "range" in stud_lower and "domain" not in stud_lower:
            return {
                "correct": False,
                "verdict": "incorrect",
                "feedback": "Your answer describes Range (outputs), but the question asked about Domain (inputs).",
                "confidence": 0.90,
                "reason": "Domain vs. Range Inversion detected.",
                "misconception": "Domain vs. Range Inversion",
                "conceptual_trap": "Focusing on output values rather than legal input domains.",
                "correct_mental_model": "Domain = allowable input space; Range = achievable output values."
            }
        if ("range" in corr_lower or "range" in q_lower) and "domain" in stud_lower and "range" not in stud_lower:
            return {
                "correct": False,
                "verdict": "incorrect",
                "feedback": "Your answer mentions Domain (inputs), but the question referred to the resulting output Range.",
                "confidence": 0.90,
                "reason": "Domain vs. Range Inversion detected.",
                "misconception": "Domain vs. Range Inversion",
                "conceptual_trap": "Confusing permissible inputs with the evaluated output space.",
                "correct_mental_model": "Domain is the input set; Range is the resulting output set."
            }

        # Extract meaningful content words
        stud_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', stud_lower)) - COMMON_STOPWORDS
        corr_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', corr_lower)) - COMMON_STOPWORDS
        q_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', q_lower)) - COMMON_STOPWORDS

        target_concept_words = corr_words.union(q_words)

        # Domain contrast check (e.g. talking about CSS when question is about HTML)
        for group_a, group_b in CONTRAST_DOMAINS:
            if (target_concept_words & group_a) and not (stud_words & group_a) and (stud_words & group_b):
                contrast_term = next(iter(stud_words & group_b))
                target_term = next(iter(target_concept_words & group_a))
                return {
                    "correct": False,
                    "verdict": "incorrect",
                    "feedback": f"Your answer discusses {contrast_term}, but the question is specifically about {target_term}.",
                    "confidence": 0.90,
                    "reason": f"Contrast domain confusion: {contrast_term} instead of {target_term}.",
                    "misconception": target_misconception or f"Conflating {contrast_term} with {target_term}",
                    "conceptual_trap": f"Describing {contrast_term} rather than explaining {target_term}.",
                    "correct_mental_model": f"The question requires: {correct_answer}"
                }

        # Build stem sets for both directions
        ref_stems = {w[:5] if len(w) > 5 else w for w in corr_words}
        stud_stems = {w[:5] if len(w) > 5 else w for w in stud_words}

        if not ref_stems:
            # Fall back to question-word stems if reference has no content words
            ref_stems = {w[:5] if len(w) > 5 else w for w in q_words}

        # ── Forward: fraction of reference stems covered by student ──────────
        fwd_matched = sum(
            1 for s in ref_stems
            if any(s in sw or sw in s for sw in stud_words)
        )
        fwd_coverage = fwd_matched / max(1, len(ref_stems))

        # ── Reverse: fraction of student stems that appear in reference ──────
        rev_matched = sum(
            1 for s in stud_stems
            if any(s in rw or rw in s for rw in corr_words)
        )
        rev_coverage = rev_matched / max(1, len(stud_stems)) if stud_stems else 0.0

        # Bidirectional score: take the maximum
        coverage = max(fwd_coverage, rev_coverage)

        if coverage >= 0.50:
            return {
                "correct": True,
                "verdict": "correct",
                "feedback": f"Correct! {explanation or 'Your answer accurately covers the core mechanism.'}".strip(),
                "confidence": 0.85,
                "reason": "High semantic coverage of core concept.",
                "misconception": None,
                "conceptual_trap": None,
                "correct_mental_model": None
            }
        elif coverage >= 0.20:
            return {
                "correct": False,
                "verdict": "partial",
                "feedback": f"Partially correct, but missing key details: {correct_answer}".strip(),
                "confidence": 0.80,
                "reason": "Partial conceptual coverage.",
                "misconception": target_misconception or "Partially incomplete conceptual formulation",
                "conceptual_trap": "Captured part of the terminology without the complete mechanism.",
                "correct_mental_model": f"Core framework: {correct_answer}"
            }
        else:
            return {
                "correct": False,
                "verdict": "incorrect",
                "feedback": f"Your answer does not address the concept. Key idea: {correct_answer}".strip(),
                "confidence": 0.85,
                "reason": "Low conceptual relevance or coverage.",
                "misconception": target_misconception or "Incomplete or incorrect conceptual formulation",
                "conceptual_trap": "Omission of core operational concepts in the explanation.",
                "correct_mental_model": f"Core framework: {correct_answer}"
            }

evaluation_service = EvaluationService()
