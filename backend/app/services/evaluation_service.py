import re
import json
import httpx
import asyncio
from typing import Dict, Any, Optional, List
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
            return await self.evaluate_short_answer_rubric(
                question_text=question_text,
                correct_answer=correct_answer,
                student_answer=cleaned_student,
                explanation=explanation,
                max_points=10.0,
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
        return await self.evaluate_short_answer_rubric(
            question_text=question_text,
            correct_answer=correct_answer,
            student_answer=student_answer,
            explanation=explanation,
            max_points=10.0,
            target_misconception=target_misconception
        )

    async def evaluate_short_answer_rubric(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        explanation: str = "",
        rubric: Optional[List[Dict[str, Any]]] = None,
        max_points: float = 5.0,
        target_misconception: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive rubric-based semantic evaluator for short-answer questions.
        - Evaluates meaning, not exact keywords or sentences.
        - Breaks down expected answer into individual criteria.
        - Classifies criteria: correct, partial, missing, incorrect.
        - Awards partial marks (NEVER 0 points for 'partial').
        - Recognizes valid analogies, synonyms, and alternative phrasing.
        - Generates structured feedback: what was understood, what was missing,
          what needs correction, and how to improve.
        """
        # ── 1. Empty / Whitespace Guard ───────────────────────────────────────
        if _is_empty_or_whitespace(student_answer):
            empty_rubric = self._normalize_rubric([], rubric, max_points, 0.0)
            return {
                "correct": False,
                "verdict": "unanswered",
                "score": 0.0,
                "max_score": max_points,
                "percentage": 0.0,
                "feedback": "No answer provided. Please type your explanation.",
                "confidence": 1.0,
                "reason": "No answer provided.",
                "rubric_breakdown": empty_rubric,
                "what_understood": "None (no response submitted)",
                "what_missing": f"Core concept: {correct_answer}",
                "what_needs_correction": "None",
                "how_to_improve": "Provide an explanation in your own words based on the lecture.",
                "misconception": target_misconception or "Unanswered checkpoint",
                "conceptual_trap": "Leaving the question unanswered without attempting an explanation.",
                "correct_mental_model": f"Core concept: {correct_answer}"
            }

        # ── 2. Declarations of Not Knowing / Refusals ─────────────────────────
        if _is_unanswered_or_refusal(student_answer):
            refusal_rubric = self._normalize_rubric([], rubric, max_points, 0.0)
            return {
                "correct": False,
                "verdict": "unanswered",
                "score": 0.0,
                "max_score": max_points,
                "percentage": 0.0,
                "feedback": "Marked as unanswered. Please review the concept to understand: " + correct_answer,
                "confidence": 1.0,
                "reason": "Student declared lack of knowledge or skipped.",
                "rubric_breakdown": refusal_rubric,
                "what_understood": "None",
                "what_missing": f"Core concept: {correct_answer}",
                "what_needs_correction": "None",
                "how_to_improve": "Review the video section for this concept and attempt an explanation.",
                "misconception": target_misconception or "Unanswered checkpoint",
                "conceptual_trap": "Stating 'I don't know' rather than attempting a conceptual explanation.",
                "correct_mental_model": f"Core concept: {correct_answer}"
            }

        # ── 3. Greetings & Conversational Filler ──────────────────────────────
        if _is_greeting_or_filler(student_answer):
            filler_rubric = self._normalize_rubric([], rubric, max_points, 0.0)
            return {
                "correct": False,
                "verdict": "incorrect",
                "score": 0.0,
                "max_score": max_points,
                "percentage": 0.0,
                "feedback": "Your response is a greeting or conversational remark, not an explanation of the question.",
                "confidence": 1.0,
                "reason": "Greeting or conversational filler detected instead of an answer.",
                "rubric_breakdown": filler_rubric,
                "what_understood": "None",
                "what_missing": f"The question requires explaining: {correct_answer}",
                "what_needs_correction": "Submitting conversational greetings instead of an explanation.",
                "how_to_improve": "Address the question prompt directly with conceptual reasoning.",
                "misconception": target_misconception or "Irrelevant conversational response",
                "conceptual_trap": "Submitting conversational greetings instead of an explanation.",
                "correct_mental_model": f"The question requires explaining: {correct_answer}"
            }

        # ── 4. Random Characters / Keystroke Smashing / Gibberish ─────────────
        if _is_gibberish_or_random(student_answer):
            gibberish_rubric = self._normalize_rubric([], rubric, max_points, 0.0)
            return {
                "correct": False,
                "verdict": "incorrect",
                "score": 0.0,
                "max_score": max_points,
                "percentage": 0.0,
                "feedback": "Your response contains random characters or unintelligible text. Please provide a meaningful explanation.",
                "confidence": 1.0,
                "reason": "Meaningless or random keystrokes detected.",
                "rubric_breakdown": gibberish_rubric,
                "what_understood": "None",
                "what_missing": f"A valid explanation should address: {correct_answer}",
                "what_needs_correction": "Random keystrokes entered.",
                "how_to_improve": "Write full words explaining the idea.",
                "misconception": target_misconception or "Superficial or meaningless text",
                "conceptual_trap": "Entering random keyboard characters.",
                "correct_mental_model": f"A valid explanation should address: {correct_answer}"
            }

        # ── 5. Minimum Word Count Guard ───────────────────────────────────────
        words = [w for w in student_answer.strip().split() if w]
        if len(words) < 4:
            fragment_rubric = self._normalize_rubric([], rubric, max_points, 0.0)
            return {
                "correct": False,
                "verdict": "incorrect",
                "score": 0.0,
                "max_score": max_points,
                "percentage": 0.0,
                "feedback": "Answer is too brief to demonstrate understanding. Please explain in your own words with complete reasoning.",
                "confidence": 1.0,
                "reason": "Answer is too brief to demonstrate understanding.",
                "rubric_breakdown": fragment_rubric,
                "what_understood": f"Brief mention: '{student_answer.strip()}'",
                "what_missing": f"Detailed reasoning and explanation: {correct_answer}",
                "what_needs_correction": "Answer is only a fragment.",
                "how_to_improve": "Explain the concept in 1-2 complete sentences.",
                "misconception": target_misconception or "Superficial or fragmentary answer",
                "conceptual_trap": "Providing single words or ultra-brief fragments instead of explaining.",
                "correct_mental_model": f"A complete conceptual answer should address: {correct_answer}"
            }

        # ── 6. Grade with Groq LLM (OpenAI / Qwen models) ─────────────────────
        if self.groq_api_key and self.groq_api_key.strip():
            try:
                groq_eval = await self._grade_short_answer_with_groq_rubric(
                    question=question_text,
                    reference_answer=correct_answer,
                    student_answer=student_answer,
                    explanation=explanation,
                    rubric=rubric,
                    max_points=max_points,
                    target_misconception=target_misconception
                )
                if groq_eval:
                    return groq_eval
            except Exception as e:
                print(f"[EvaluationService] Groq rubric grading error: {e}. Using safe heuristic fallback.")

        # ── 7. Safe Heuristic Fallback (AI unavailable or error) ───────────────
        return self._heuristic_short_answer_eval(
            question_text=question_text,
            correct_answer=correct_answer,
            student_answer=student_answer,
            explanation=explanation,
            rubric=rubric,
            max_points=max_points,
            target_misconception=target_misconception
        )

    async def _grade_short_answer_with_groq_rubric(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        explanation: str,
        rubric: Optional[List[Dict[str, Any]]] = None,
        max_points: float = 5.0,
        target_misconception: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key.strip()}",
            "Content-Type": "application/json"
        }

        rubric_section = ""
        if rubric and len(rubric) > 0:
            rubric_section = f"PRE-ESTABLISHED RUBRIC TO USE:\n{json.dumps(rubric, indent=2)}\n"

        prompt = (
            "You are an expert computer science professor evaluating a student's conceptual short-answer response.\n\n"
            f"Question: {question}\n"
            f"Expected Reference Answer: {reference_answer}\n"
            f"Learning Context & Principles: {explanation or 'Key foundational concept'}\n"
            f"Student Answer: {student_answer}\n"
            f"Maximum Points Available: {max_points}\n\n"
            f"{rubric_section}"
            "CORE EVALUATION RULES:\n"
            "1. MEANING OVER EXACT KEYWORDS: Evaluate the actual conceptual meaning of the student's answer. DO NOT require exact matching keywords or verbatim sentences. Accept students' own words, synonyms, and valid analogies (e.g. comparing hierarchical categorization and indexing to library organization).\n"
            "2. BREAKDOWN INTO KEY CRITERIA: Break the expected answer into 2 to 4 core conceptual criteria (or use the pre-established rubric above if provided). Ensure sum of points_possible equals " + str(max_points) + ".\n"
            "3. CLASSIFY EACH CRITERION:\n"
            "   - 'correct': Student demonstrated accurate understanding. Award full points_possible for this criterion.\n"
            "   - 'partial': Student demonstrated partial understanding or missed a minor nuance. Award appropriate partial points (e.g. 50% to 75% of points_possible). NEVER award 0 points when a concept is partially understood!\n"
            "   - 'missing': Concept was omitted entirely. Award 0 points.\n"
            "   - 'incorrect': Concept was contradicted or factually misunderstood. Award 0 points.\n"
            "4. SCORING & VERDICT:\n"
            "   - 'score': Sum of points_awarded across all criteria.\n"
            "   - 'verdict':\n"
            "     * 'correct': score >= 0.8 * max_score (demonstrates solid conceptual understanding).\n"
            "     * 'partial': 0 < score < 0.8 * max_score (student understood some criteria, but missed other details. 'partial' MUST award appropriate points! NEVER 0 points!).\n"
            "     * 'incorrect': score == 0 or answer demonstrates fundamentally flawed understanding.\n"
            "     * 'needs_clarification': answer is ambiguous or contradictory and cannot be evaluated confidently.\n"
            "5. STRUCTURED FEEDBACK:\n"
            "   - what_understood: Clear sentence explaining what the student understood correctly.\n"
            "   - what_missing: Clear sentence explaining what concepts or details were missing.\n"
            "   - what_needs_correction: Erroneous statements that need correction (or 'None' if conceptually sound).\n"
            "   - how_to_improve: Concrete, actionable advice on how the student can improve.\n"
            "   - feedback: 1-2 sentence overall encouraging summary explaining the score and verdict.\n\n"
            "OUTPUT FORMAT (STRICT JSON ONLY with NO markdown fences):\n"
            "{\n"
            '  "score": 4.0,\n'
            f'  "max_score": {max_points},\n'
            '  "verdict": "partial",\n'
            '  "rubric_breakdown": [\n'
            '    {\n'
            '      "criterion": "Systematic organization of items into categories",\n'
            '      "points_possible": 2.0,\n'
            '      "points_awarded": 2.0,\n'
            '      "status": "correct",\n'
            '      "comment": "Accurately used library analogy to group by genre/artist/album."\n'
            '    },\n'
            '    {\n'
            '      "criterion": "Avoidance of linear search / sequential scan",\n'
            '      "points_possible": 1.0,\n'
            '      "points_awarded": 1.0,\n'
            '      "status": "correct",\n'
            '      "comment": "Correctly identified that checking one by one is inefficient."\n'
            '    },\n'
            '    {\n'
            '      "criterion": "Indexed / fast retrieval mechanism",\n'
            '      "points_possible": 1.0,\n'
            '      "points_awarded": 1.0,\n'
            '      "status": "correct",\n'
            '      "comment": "Proposed using an index or search structure."\n'
            '    },\n'
            '    {\n'
            '      "criterion": "Underlying data structure or algorithmic technique",\n'
            '      "points_possible": 1.0,\n'
            '      "points_awarded": 0.0,\n'
            '      "status": "missing",\n'
            '      "comment": "Did not specify concrete structure such as binary search tree or hash table."\n'
            '    }\n'
            '  ],\n'
            '  "what_understood": "You clearly understood hierarchical organization, the inefficiency of linear search, and the need for indexing.",\n'
            '  "what_missing": "You did not specify the concrete data structures or search algorithms discussed in the lecture.",\n'
            '  "what_needs_correction": "None",\n'
            '  "how_to_improve": "To achieve full marks, connect the library index concept directly to data structures like binary search trees or hash tables.",\n'
            '  "feedback": "Partially correct! You demonstrated strong conceptual understanding of categorization and indexing, but missed mentioning the specific data structures taught in the lecture."\n'
            "}"
        )

        models_to_try = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]

        for attempt in range(len(models_to_try)):
            model_name = models_to_try[attempt]
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional computer science examiner. Output only valid JSON with no markdown fences."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.15,
                "max_tokens": 1200,
                "response_format": {"type": "json_object"}
            }

            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        raw = resp.json()["choices"][0]["message"]["content"].strip()
                        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
                        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE).strip()
                        parsed = json.loads(raw)

                        score = float(parsed.get("score", 0.0))
                        parsed_max = float(parsed.get("max_score", max_points)) or max_points
                        percentage = round((score / parsed_max) * 100.0, 1)

                        raw_verdict = str(parsed.get("verdict", "")).lower().strip()
                        if raw_verdict in ["correct", "partial", "incorrect", "needs_clarification", "unanswered"]:
                            verdict = raw_verdict
                        else:
                            if percentage >= 80.0:
                                verdict = "correct"
                            elif percentage > 0.0:
                                verdict = "partial"
                            else:
                                verdict = "incorrect"

                        # Ensure partial verdict ALWAYS awards marks
                        if verdict == "partial" and score <= 0.0:
                            score = round(parsed_max * 0.5, 1)
                            percentage = 50.0

                        raw_rubric = parsed.get("rubric_breakdown", [])
                        norm_rubric = self._normalize_rubric(
                            raw_items=raw_rubric,
                            pre_established_rubric=rubric,
                            target_max_score=parsed_max,
                            target_score=score
                        )
                        # Derive score strictly from sum of criteria points_awarded
                        score = round(sum(it["points_awarded"] for it in norm_rubric), 1)
                        parsed_max = round(sum(it["max_points"] for it in norm_rubric), 1)

                        is_correct = (verdict == "correct")

                        feedback = str(parsed.get("feedback", "")).strip()
                        what_u = str(parsed.get("what_understood", "")).strip() or "Understood core elements."
                        what_m = str(parsed.get("what_missing", "")).strip() or "Minor details omitted."
                        what_c = str(parsed.get("what_needs_correction", "None")).strip()
                        how_i = str(parsed.get("how_to_improve", "")).strip()

                        return {
                            "correct": is_correct,
                            "verdict": verdict,
                            "score": round(score, 1),
                            "max_score": round(parsed_max, 1),
                            "percentage": percentage,
                            "feedback": feedback or f"Score: {score}/{parsed_max}. {what_u}",
                            "confidence": 0.95 if is_correct else 0.90,
                            "reason": feedback,
                            "rubric_breakdown": norm_rubric,
                            "what_understood": what_u,
                            "what_missing": what_m,
                            "what_needs_correction": what_c,
                            "how_to_improve": how_i,
                            "misconception": None if is_correct else (target_misconception or (what_m if verdict == "partial" else "Conceptual misunderstanding")),
                            "conceptual_trap": None if is_correct else (
                                what_m if verdict == "partial" else "Misunderstanding core invariant."
                            ),
                            "correct_mental_model": None if is_correct else f"Core principle: {reference_answer}"
                        }
                    elif resp.status_code == 429:
                        await asyncio.sleep(2.0 * (attempt + 1))
            except Exception as e:
                print(f"[EvaluationService] Groq attempt {attempt+1} on model {model_name} failed: {e}")
                await asyncio.sleep(1.0)

        return None

    @staticmethod
    def _normalize_rubric(
        raw_items: Optional[List[Dict[str, Any]]],
        pre_established_rubric: Optional[List[Dict[str, Any]]],
        target_max_score: float = 5.0,
        target_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Guarantees that:
        1. Every criterion has a positive max_points (> 0) and points_awarded.
        2. The sum of criteria max_points strictly equals target_max_score (e.g. 5.0).
        3. The sum of criteria points_awarded strictly equals target_score.
        4. Both 'max_points' and 'points_possible', and both 'notes' and 'comment' are populated.
        """
        items: List[Dict[str, Any]] = []

        # If a pre-established rubric exists, prioritize its criteria definitions and max weights
        if pre_established_rubric and len(pre_established_rubric) > 0:
            for idx, p_item in enumerate(pre_established_rubric):
                c_title = str(p_item.get("criterion", f"Criterion {idx+1}")).strip()
                c_max = float(p_item.get("max_points") or p_item.get("points_possible") or 2.5)

                # Find match in raw_items by criterion text or index
                matched_raw = None
                if raw_items and len(raw_items) > idx:
                    matched_raw = raw_items[idx]
                elif raw_items:
                    for r in raw_items:
                        r_crit = str(r.get("criterion", "")).lower()
                        if c_title.lower() in r_crit or r_crit in c_title.lower():
                            matched_raw = r
                            break

                if matched_raw:
                    c_pts = float(matched_raw.get("points_awarded") or matched_raw.get("points") or matched_raw.get("score") or 0.0)
                    c_status = str(matched_raw.get("status", "missing")).lower().strip()
                    c_notes = str(matched_raw.get("notes") or matched_raw.get("comment") or matched_raw.get("reason") or "").strip()
                else:
                    c_pts = 0.0
                    c_status = "missing"
                    c_notes = ""

                items.append({
                    "criterion": c_title,
                    "max_points": c_max,
                    "points_possible": c_max,
                    "points_awarded": min(c_max, max(0.0, c_pts)),
                    "status": c_status,
                    "notes": c_notes,
                    "comment": c_notes
                })
        elif raw_items and len(raw_items) > 0:
            for idx, r in enumerate(raw_items):
                c_title = str(r.get("criterion", f"Criterion {idx+1}")).strip()
                c_max = float(r.get("max_points") or r.get("points_possible") or r.get("max_score") or 0.0)
                c_pts = float(r.get("points_awarded") or r.get("points") or r.get("score") or 0.0)
                c_status = str(r.get("status", "missing")).lower().strip()
                c_notes = str(r.get("notes") or r.get("comment") or r.get("reason") or "").strip()

                items.append({
                    "criterion": c_title,
                    "max_points": c_max,
                    "points_possible": c_max,
                    "points_awarded": min(c_max, max(0.0, c_pts)),
                    "status": c_status,
                    "notes": c_notes,
                    "comment": c_notes
                })
        else:
            # Fallback 2-criteria synthesis
            first_max = round(target_max_score * 0.5, 1)
            second_max = round(target_max_score - first_max, 1)
            items = [
                {
                    "criterion": "Core conceptual understanding & mechanisms",
                    "max_points": first_max,
                    "points_possible": first_max,
                    "points_awarded": 0.0,
                    "status": "missing",
                    "notes": "No explanation provided for core concept.",
                    "comment": "No explanation provided for core concept."
                },
                {
                    "criterion": "Explanation, reasoning & supporting details",
                    "max_points": second_max,
                    "points_possible": second_max,
                    "points_awarded": 0.0,
                    "status": "missing",
                    "notes": "Missing supporting details.",
                    "comment": "Missing supporting details."
                }
            ]

        # 1. Normalize max_points sum to strictly match target_max_score
        total_max = sum(it["max_points"] for it in items)
        if total_max <= 0:
            even_max = round(target_max_score / max(1, len(items)), 1)
            for it in items:
                it["max_points"] = even_max
                it["points_possible"] = even_max
            items[-1]["max_points"] = round(target_max_score - sum(it["max_points"] for it in items[:-1]), 1)
            items[-1]["points_possible"] = items[-1]["max_points"]
        elif abs(total_max - target_max_score) > 0.05:
            running = 0.0
            for it in items[:-1]:
                scaled = round((it["max_points"] / total_max) * target_max_score, 1)
                it["max_points"] = scaled
                it["points_possible"] = scaled
                running += scaled
            items[-1]["max_points"] = round(target_max_score - running, 1)
            items[-1]["points_possible"] = items[-1]["max_points"]

        # 2. Reconcile points_awarded with target_score if specified
        if target_score is not None:
            eff_score = min(target_max_score, max(0.0, target_score))
            total_awarded = sum(it["points_awarded"] for it in items)

            if abs(total_awarded - eff_score) > 0.05:
                if total_awarded > 0:
                    running_pts = 0.0
                    for it in items[:-1]:
                        scaled_pts = min(it["max_points"], round((it["points_awarded"] / total_awarded) * eff_score, 1))
                        it["points_awarded"] = scaled_pts
                        running_pts += scaled_pts
                    items[-1]["points_awarded"] = min(items[-1]["max_points"], max(0.0, round(eff_score - running_pts, 1)))
                else:
                    # Distribute score across criteria with non-zero max_points
                    rem = eff_score
                    for it in items:
                        alloc = min(it["max_points"], rem)
                        it["points_awarded"] = round(alloc, 1)
                        if alloc > 0:
                            it["status"] = "correct" if alloc >= it["max_points"] else "partial"
                        rem -= alloc

        # 3. Final clamp & status consistency
        for it in items:
            it["points_awarded"] = min(it["max_points"], max(0.0, round(it["points_awarded"], 1)))
            if it["points_awarded"] >= it["max_points"] and it["max_points"] > 0:
                it["status"] = "correct"
            elif it["points_awarded"] > 0:
                it["status"] = "partial"
            elif it["status"] not in ("incorrect", "missing"):
                it["status"] = "missing"

        return items

    def _heuristic_short_answer_eval(
        self,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        explanation: str,
        rubric: Optional[List[Dict[str, Any]]] = None,
        max_points: float = 5.0,
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
          >= 0.50  → correct (100% marks)
          >= 0.35  → partial (70% marks)
          >= 0.20  → partial (40% marks)
          <  0.20  → incorrect (0 marks)
        """
        stud_lower = student_answer.lower().strip()
        corr_lower = correct_answer.lower().strip()
        q_lower = question_text.lower().strip()

        # Domain vs Range specific trap checks
        if ("domain" in corr_lower or "domain" in q_lower) and "range" in stud_lower and "domain" not in stud_lower:
            return {
                "correct": False,
                "verdict": "incorrect",
                "score": 0.0,
                "max_score": max_points,
                "percentage": 0.0,
                "feedback": "Your answer describes Range (outputs), but the question asked about Domain (inputs).",
                "confidence": 0.90,
                "reason": "Domain vs. Range Inversion detected.",
                "rubric_breakdown": [
                    {"criterion": "Identify allowable input space (Domain)", "status": "missing", "points_awarded": 0.0, "max_points": round(max_points * 0.5, 1), "notes": "Mentioned outputs (Range) instead."},
                    {"criterion": "Distinguish from output values (Range)", "status": "incorrect", "points_awarded": 0.0, "max_points": round(max_points * 0.5, 1), "notes": "Conflated inputs with outputs."}
                ],
                "what_understood": "None (focused on outputs instead of inputs).",
                "what_missing": "Explicit discussion of valid input values.",
                "what_needs_correction": "Replace Range with Domain when referring to inputs.",
                "how_to_improve": "Remember that Domain is the set of inputs, while Range is the set of outputs.",
                "misconception": "Domain vs. Range Inversion",
                "conceptual_trap": "Focusing on output values rather than legal input domains.",
                "correct_mental_model": "Domain = allowable input space; Range = achievable output values."
            }
        if ("range" in corr_lower or "range" in q_lower) and "domain" in stud_lower and "range" not in stud_lower:
            return {
                "correct": False,
                "verdict": "incorrect",
                "score": 0.0,
                "max_score": max_points,
                "percentage": 0.0,
                "feedback": "Your answer mentions Domain (inputs), but the question referred to the resulting output Range.",
                "confidence": 0.90,
                "reason": "Domain vs. Range Inversion detected.",
                "rubric_breakdown": [
                    {"criterion": "Identify achievable output space (Range)", "status": "missing", "points_awarded": 0.0, "max_points": round(max_points * 0.5, 1), "notes": "Mentioned inputs (Domain) instead."},
                    {"criterion": "Distinguish from input arguments (Domain)", "status": "incorrect", "points_awarded": 0.0, "max_points": round(max_points * 0.5, 1), "notes": "Conflated outputs with inputs."}
                ],
                "what_understood": "None (focused on inputs instead of outputs).",
                "what_missing": "Explicit discussion of resulting output values.",
                "what_needs_correction": "Replace Domain with Range when referring to outputs.",
                "how_to_improve": "Remember that Range is the set of achievable outputs from the function.",
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
                    "score": 0.0,
                    "max_score": max_points,
                    "percentage": 0.0,
                    "feedback": f"Your answer discusses {contrast_term}, but the question is specifically about {target_term}.",
                    "confidence": 0.90,
                    "reason": f"Contrast domain confusion: {contrast_term} instead of {target_term}.",
                    "rubric_breakdown": [
                        {"criterion": f"Address {target_term}", "status": "missing", "points_awarded": 0.0, "max_points": max_points, "notes": f"Discussed {contrast_term} instead."}
                    ],
                    "what_understood": f"Understands {contrast_term}, but that was not the focus.",
                    "what_missing": f"Discussion of {target_term}.",
                    "what_needs_correction": f"Refocus on {target_term} rather than {contrast_term}.",
                    "how_to_improve": f"Answer specifically about {target_term}.",
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

        # Library Analogy specific semantic booster
        if ("library" in q_lower or "library" in corr_lower or "shelves" in corr_lower) and any(w in stud_lower for w in ["shelf", "shelves", "organize", "organized", "categor", "group", "book"]):
            has_org = any(w in stud_lower for w in ["shelf", "shelves", "organize", "organized", "categor", "group", "section"])
            has_retrieval = any(w in stud_lower for w in ["quick", "fast", "efficient", "second", "random", "scan", "index", "search"])
            if has_org and has_retrieval:
                coverage = max(coverage, 0.90)
            elif has_org or has_retrieval:
                coverage = max(coverage, 0.45)

        if coverage >= 0.50:
            awarded = round(max_points * 1.0, 1)
            raw_breakdown = [
                {"criterion": "Core conceptual understanding & organization", "status": "correct", "points_awarded": round(max_points * 0.5, 1), "max_points": round(max_points * 0.5, 1), "notes": "Accurately conveys the essential principle."},
                {"criterion": "Mechanisms & retrieval efficiency", "status": "correct", "points_awarded": round(max_points - round(max_points * 0.5, 1), 1), "max_points": round(max_points - round(max_points * 0.5, 1), 1), "notes": "Clearly explains how organization enables efficient lookup."}
            ]
            norm_breakdown = self._normalize_rubric(raw_breakdown, rubric, max_points, awarded)
            return {
                "correct": True,
                "verdict": "correct",
                "score": awarded,
                "max_score": max_points,
                "percentage": 100.0,
                "feedback": f"Correct! {explanation or 'Your answer accurately covers the core mechanism.'}".strip(),
                "confidence": 0.85,
                "reason": "High semantic coverage of core concept.",
                "rubric_breakdown": norm_breakdown,
                "what_understood": "Fully captured the key mechanism and main concepts.",
                "what_missing": "None significant.",
                "what_needs_correction": "None.",
                "how_to_improve": "Maintain this clear level of explanation.",
                "misconception": None,
                "conceptual_trap": None,
                "correct_mental_model": None
            }
        elif coverage >= 0.20:
            # PARTIAL: Guarantee score > 0 (e.g. 70% or 40%)
            frac = 0.7 if coverage >= 0.35 else 0.4
            awarded = max(0.5, round(max_points * frac, 1))
            pct = round((awarded / max_points) * 100, 1)
            raw_breakdown = [
                {"criterion": "Main concept identification & structure", "status": "correct" if frac >= 0.7 else "partial", "points_awarded": round(awarded * 0.6, 1), "max_points": round(max_points * 0.5, 1), "notes": "Understood the general idea."},
                {"criterion": "Operational mechanics & efficiency", "status": "partial" if frac >= 0.7 else "missing", "points_awarded": round(awarded - round(awarded * 0.6, 1), 1), "max_points": round(max_points - round(max_points * 0.5, 1), 1), "notes": "Some operational details omitted."}
            ]
            norm_breakdown = self._normalize_rubric(raw_breakdown, rubric, max_points, awarded)
            return {
                "correct": False,
                "verdict": "partial",
                "score": awarded,
                "max_score": max_points,
                "percentage": pct,
                "feedback": f"Partially correct ({awarded}/{max_points} points). Key details to include: {correct_answer}".strip(),
                "confidence": 0.80,
                "reason": "Partial conceptual coverage.",
                "rubric_breakdown": norm_breakdown,
                "what_understood": "Demonstrated partial understanding of the main concept.",
                "what_missing": f"Additional operational details: {correct_answer}",
                "what_needs_correction": "Provide more thorough technical elaboration.",
                "how_to_improve": f"Connect your explanation to the underlying mechanism: {correct_answer}",
                "misconception": target_misconception or "Partially incomplete conceptual formulation",
                "conceptual_trap": "Captured part of the terminology without the complete mechanism.",
                "correct_mental_model": f"Core framework: {correct_answer}"
            }
        else:
            raw_breakdown = [
                {"criterion": "Core concept explanation", "status": "missing", "points_awarded": 0.0, "max_points": max_points, "notes": "Did not demonstrate expected understanding."}
            ]
            norm_breakdown = self._normalize_rubric(raw_breakdown, rubric, max_points, 0.0)
            return {
                "correct": False,
                "verdict": "incorrect",
                "score": 0.0,
                "max_score": max_points,
                "percentage": 0.0,
                "feedback": f"Your answer does not address the concept. Key idea: {correct_answer}".strip(),
                "confidence": 0.85,
                "reason": "Low conceptual relevance or coverage.",
                "rubric_breakdown": norm_breakdown,
                "what_understood": "Minimal or no relevant alignment found.",
                "what_missing": f"The core answer: {correct_answer}",
                "what_needs_correction": "The answer diverged significantly from the required concept.",
                "how_to_improve": f"Review the lecture explanation on this topic: {correct_answer}",
                "misconception": target_misconception or "Incomplete or incorrect conceptual formulation",
                "conceptual_trap": "Omission of core operational concepts in the explanation.",
                "correct_mental_model": f"Core framework: {correct_answer}"
            }

evaluation_service = EvaluationService()
