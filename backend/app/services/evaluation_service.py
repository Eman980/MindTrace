import json
import httpx
from typing import Dict, Any, Optional
from app.config import settings

class EvaluationService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY

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
            "confidence": float,
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
        if self.api_key:
            try:
                llm_eval = await self._evaluate_short_answer_with_llm(
                    question_text, correct_answer, student_answer, explanation, target_misconception
                )
                if llm_eval:
                    return llm_eval
            except Exception as e:
                print(f"[EvaluationService] LLM evaluation error: {e}. Using rule-based fallback.")

        # Heuristic / Rule-based evaluation
        stud_lower = student_answer.lower()
        corr_lower = correct_answer.lower()
        
        if "domain" in corr_lower and "range" in stud_lower:
            return {
                "correct": False,
                "confidence": 0.88,
                "reason": "Your answer suggests Range (outputs), but the question asked about Domain (inputs).",
                "misconception": "Domain vs. Range Inversion",
                "conceptual_trap": "Focusing on output values rather than legal input domains.",
                "correct_mental_model": "Domain = allowable input space; Range = achievable output values."
            }
        if "range" in corr_lower and "domain" in stud_lower:
            return {
                "correct": False,
                "confidence": 0.88,
                "reason": "Your answer mentions Domain (inputs), but the question referred to the resulting output Range.",
                "misconception": "Domain vs. Range Inversion",
                "conceptual_trap": "Confusing permissible inputs with the evaluated output space.",
                "correct_mental_model": "Domain is the input set; Range is the resulting output set."
            }
            
        key_words = [w for w in corr_lower.replace(",", "").replace(".", "").split() if len(w) > 3]
        matches = [w for w in key_words if w in stud_lower]
        match_ratio = len(matches) / max(1, len(key_words))
        
        if match_ratio >= 0.4 or corr_lower in stud_lower or stud_lower in corr_lower:
            return {
                "correct": True,
                "confidence": 0.85,
                "reason": f"Well explained! {explanation}".strip(),
                "misconception": None,
                "conceptual_trap": None,
                "correct_mental_model": None
            }
        else:
            return {
                "correct": False,
                "confidence": 0.80,
                "reason": f"Not quite. Key points to remember: {correct_answer}. {explanation}".strip(),
                "misconception": target_misconception or "Incomplete conceptual formulation of the topic",
                "conceptual_trap": "Omission of core operational constraints and criteria in the explanation.",
                "correct_mental_model": f"Core framework: {correct_answer}"
            }

    async def _evaluate_short_answer_with_llm(
        self,
        question: str,
        reference_answer: str,
        student_answer: str,
        explanation: str,
        target_misconception: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = (
            "Evaluate the student's short answer for conceptual correctness.\n"
            f"Question: {question}\n"
            f"Reference Model Answer: {reference_answer}\n"
            f"Student Answer: {student_answer}\n"
            f"Target Misconception to diagnose: {target_misconception or 'None specified'}\n\n"
            "Return valid JSON with keys:\n"
            "- correct (boolean)\n"
            "- confidence (float between 0.0 and 1.0)\n"
            "- reason (clear, encouraging student-facing explanation of 1-2 sentences)\n"
            "- misconception (string identifying specific misconception if incorrect, else null)\n"
            "- conceptual_trap (string explaining WHY the mistake is an intuitive trap if incorrect, else null)\n"
            "- correct_mental_model (string stating the exact rule/framework needed to resolve it, else null)"
        )
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a warm, rigorous university computer science professor. Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = json.loads(data["choices"][0]["message"]["content"])
                return {
                    "correct": bool(content.get("correct", False)),
                    "confidence": float(content.get("confidence", 0.9)),
                    "reason": str(content.get("reason", explanation)),
                    "misconception": content.get("misconception"),
                    "conceptual_trap": content.get("conceptual_trap"),
                    "correct_mental_model": content.get("correct_mental_model")
                }
        return None

evaluation_service = EvaluationService()
