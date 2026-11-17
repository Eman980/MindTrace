import json
import httpx
import re
import asyncio
import random
from typing import List, Dict, Any, Optional
from app.config import settings

SAMPLE_CONCEPT_CHECKPOINTS = {
    "Introduction & Definition of a Function": [
        {
            "question_type": "mcq",
            "question_text": "What is the primary role of a mathematical and programming function?",
            "options": [
                "A. Maps each valid input to exactly one output",
                "B. Stores variables permanently in a database",
                "C. Deletes temporary memory after every line of code",
                "D. Multiplies random values repeatedly"
            ],
            "correct_answer": "A. Maps each valid input to exactly one output",
            "explanation": "A function is defined as a mapping rule that takes permissible inputs and produces a predictable single output.",
            "item_family_role": "original",
            "target_misconception": "Treating functions as random or multi-valued procedures",
            "source_excerpt": "A function is fundamentally a mapping from an input to an output. You give it a valid input value from a predetermined set, and it produces exactly one corresponding output value.",
            "source_timestamp": 38.0,
            "source_end_timestamp": 95.0
        },
        {
            "question_type": "short",
            "question_text": "In your own words, why is a function described as a 'black box'?",
            "options": [],
            "correct_answer": "It takes inputs and returns an output based on internal logic without requiring the caller to know the internal implementation.",
            "explanation": "Callers rely on the inputs and output contract without depending on internal execution details.",
            "item_family_role": "original",
            "target_misconception": "Assuming callers must manipulate internal function scope",
            "source_excerpt": "In programming, think of it as a black box with defined inputs and a predictable return value.",
            "source_timestamp": 38.0,
            "source_end_timestamp": 95.0
        }
    ],
    "Inputs, Outputs & Pure Function Mechanics": [
        {
            "question_type": "mcq",
            "question_text": "What characterizes a 'pure function' in software design?",
            "options": [
                "A. It writes changes directly to global system files",
                "B. Its output depends only on its inputs and causes no hidden side effects",
                "C. It cannot return any value to the caller",
                "D. It can only execute once during program lifetime"
            ],
            "correct_answer": "B. Its output depends only on its inputs and causes no hidden side effects",
            "explanation": "Pure functions guarantee determinism: the same inputs will always yield identical outputs without modifying exterior state.",
            "item_family_role": "original",
            "target_misconception": "Belief that pure functions rely on global variables",
            "source_excerpt": "Crucially, a pure function does not alter hidden global state; it purely transforms its provided inputs into outputs.",
            "source_timestamp": 95.0,
            "source_end_timestamp": 170.0
        }
    ],
    "Domain and Range Distinction": [
        {
            "question_type": "mcq",
            "question_text": "Which statement correctly distinguishes Domain and Range?",
            "options": [
                "A. Domain is the set of valid inputs; Range is the set of resulting outputs",
                "B. Domain is the function's return value; Range is the parameter count",
                "C. Range is the input set; Domain is the error boundary",
                "D. Domain and Range are interchangeable terms for loop counters"
            ],
            "correct_answer": "A. Domain is the set of valid inputs; Range is the set of resulting outputs",
            "explanation": "Domain governs what can safely enter the function; Range is what the function can actually output.",
            "item_family_role": "original",
            "target_misconception": "Confusing Domain (inputs) with Range (outputs)",
            "source_excerpt": "The Domain is the complete set of all permissible input values that the function can accept without error or undefined behavior. The Range, on the other hand, is the set of all resulting output values produced by applying the function over its domain. Remember: Domain belongs to inputs; Range belongs to outputs.",
            "source_timestamp": 170.0,
            "source_end_timestamp": 265.0
        },
        {
            "question_type": "short",
            "question_text": "If a function f(x) produces output values between 0 and 100, is that set of values the Domain or the Range?",
            "options": [],
            "correct_answer": "Range",
            "explanation": "The set of resulting output values generated by a function is called its Range.",
            "item_family_role": "original",
            "target_misconception": "Equating output constraints with domain inputs",
            "source_excerpt": "The Range, on the other hand, is the set of all resulting output values produced by applying the function over its domain.",
            "source_timestamp": 170.0,
            "source_end_timestamp": 265.0
        }
    ],
    "Function Notation & Syntax": [
        {
            "question_type": "mcq",
            "question_text": "In the standard notation f(x) = y, what does 'x' signify?",
            "options": [
                "A. The name of the function",
                "B. The input argument passed into the function",
                "C. The final returned result",
                "D. The runtime memory address"
            ],
            "correct_answer": "B. The input argument passed into the function",
            "explanation": "In f(x), 'f' is the identifier/name of the function, and 'x' represents the input parameter or argument.",
            "item_family_role": "original",
            "target_misconception": "Confusing input variable with function identifier or output",
            "source_excerpt": "Notice how f corresponds to the function name, x is the input parameter, and the expression defines the mapping rule.",
            "source_timestamp": 265.0,
            "source_end_timestamp": 345.0
        }
    ],
    "Concrete Examples & Domain Constraints": [
        {
            "question_type": "mcq",
            "question_text": "For the function f(x) = x², if the domain is all real numbers, what is the resulting range?",
            "options": [
                "A. All real numbers including negative numbers",
                "B. All non-negative real numbers (values >= 0)",
                "C. Only negative integers",
                "D. Exactly zero"
            ],
            "correct_answer": "B. All non-negative real numbers (values >= 0)",
            "explanation": "Squaring any real number yields zero or a positive quantity, so the range is [0, infinity).",
            "item_family_role": "original",
            "target_misconception": "Assuming negative outputs can emerge from squaring real inputs",
            "source_excerpt": "Consider f(x) = x squared. If your domain is all real numbers, what is your range? Because any real number squared is non-negative, the range is all numbers greater than or equal to zero!",
            "source_timestamp": 345.0,
            "source_end_timestamp": 420.0
        }
    ]
}

REVIEW_CHECKPOINTS = {
    "Domain vs Range": {
        "question_type": "mcq",
        "question_text": "Review Checkpoint: For a square root function f(x) = sqrt(x), what is the Domain?",
        "options": [
            "A. All non-negative real numbers x >= 0 (inputs)",
            "B. Only negative numbers (inputs)",
            "C. The output y-values exclusively",
            "D. Any string of characters"
        ],
        "correct_answer": "A. All non-negative real numbers x >= 0 (inputs)",
        "explanation": "Because we cannot take the real square root of negative numbers, the valid inputs (Domain) are x >= 0.",
        "item_family_role": "variant",
        "target_misconception": "Confusing Domain (inputs) with Range (outputs)",
        "source_excerpt": "The Domain is the complete set of all permissible input values that the function can accept without error or undefined behavior.",
        "source_timestamp": 170.0,
        "source_end_timestamp": 265.0
    },
    "Function Notation": {
        "question_type": "mcq",
        "question_text": "Review Checkpoint: Given g(t) = 3t + 1, if we pass t = 4, what is the output value?",
        "options": [
            "A. 13",
            "B. 7",
            "C. 12",
            "D. 4"
        ],
        "correct_answer": "A. 13",
        "explanation": "Substituting input t = 4 into the notation yields 3*(4) + 1 = 13.",
        "item_family_role": "variant",
        "target_misconception": "Incorrect variable binding in function notation",
        "source_excerpt": "Notice how f corresponds to the function name, x is the input parameter, and the expression defines the mapping rule.",
        "source_timestamp": 265.0,
        "source_end_timestamp": 345.0
    }
}


class CheckpointService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", "")

    def get_checkpoints_for_concept(self, concept_title: str) -> List[Dict[str, Any]]:
        for title_key, q_list in SAMPLE_CONCEPT_CHECKPOINTS.items():
            if title_key.lower() in concept_title.lower() or concept_title.lower() in title_key.lower():
                return q_list
                
        return [
            {
                "question_type": "mcq",
                "difficulty": "easy",
                "question_text": f"What is the core takeaway from '{concept_title}'?",
                "options": [
                    "A. It establishes fundamental rules and operations for this concept segment.",
                    "B. It negates prior computer science definitions.",
                    "C. It is purely optional and has no practical application.",
                    "D. It only applies to deprecated software."
                ],
                "correct_answer": "A. It establishes fundamental rules and operations for this concept segment.",
                "explanation": f"Understanding {concept_title} allows you to correctly apply these core principles.",
                "item_family_role": "original",
                "target_misconception": f"Misunderstanding core purpose of {concept_title}"
            }
        ]

    def get_review_checkpoint(self, concept_name: str) -> Dict[str, Any]:
        for key, cp in REVIEW_CHECKPOINTS.items():
            if key.lower() in concept_name.lower() or concept_name.lower() in key.lower():
                return cp
        return {
            "question_type": "mcq",
            "difficulty": "easy",
            "question_text": f"Review Checkpoint: Having reviewed '{concept_name}', how do you now apply this principle accurately?",
            "options": [
                "A. By strictly adhering to the proper definition and verifying input/output contracts",
                "B. By guessing based on intuition without checking constraints",
                "C. By ignoring the mathematical foundations",
                "D. By treating inputs and outputs as identical"
            ],
            "correct_answer": "A. By strictly adhering to the proper definition and verifying input/output contracts",
            "explanation": "Accurate conceptual understanding requires distinguishing core definitions and applying verified rules.",
            "item_family_role": "variant",
            "target_misconception": f"Shallow application of {concept_name}"
        }

    # ── UNIFIED LECTURE CHECKPOINT GENERATION ──────────────────────────────────

    @staticmethod
    def _target_count_for_concept(concept: Dict[str, Any], min_per_lecture: int, num_concepts: int) -> int:
        """
        Calculate how many questions to request for one concept:
        - Base: 2 MCQ + 1 short = 3
        - +1 per every 2 minutes of concept duration, capped at 6
        - Lecture-level minimum: spread `min_per_lecture` evenly across concepts
          so a single-concept lecture always requests at least min_per_lecture questions.
        """
        duration_secs = float(concept.get("end_time", 0)) - float(concept.get("start_time", 0))
        duration_mins = max(0.0, duration_secs / 60.0)
        base = 3  # 2 MCQ + 1 short
        extra = int(duration_mins / 2)  # +1 per 2 minutes
        per_concept_cap = 6
        from_duration = min(base + extra, per_concept_cap)
        # Spread lecture minimum across concepts (ceiling division)
        from_minimum = -(-min_per_lecture // max(num_concepts, 1))  # ceil division
        return max(from_duration, from_minimum)

    async def generate_lecture_checkpoints(
        self,
        concepts: List[Dict[str, Any]],
        full_transcript: str = "",
        lecture_title: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Generates diagnostic checkpoint questions per concept:
          • Base: 2 MCQ + 1 short answer per concept
          • +1 question per 2 minutes of concept duration, capped at 6 per concept
          • Lecture-level minimum of 4 questions regardless of concept count
          • All questions grounded in that concept's own transcript segment
          • No placeholder / heuristic questions — fails loudly if LLM returns nothing
        """
        if not concepts:
            return []

        has_api_key = bool(
            (self.groq_api_key and self.groq_api_key.strip()) or
            (self.api_key and self.api_key.strip())
        )
        if not has_api_key:
            raise RuntimeError("Checkpoint generation failed: No AI API key configured.")

        llm_items = await self._generate_lecture_checkpoints_with_llm(
            concepts=concepts,
            full_transcript=full_transcript,
            lecture_title=lecture_title
        )
        if not llm_items:
            raise RuntimeError("Checkpoint generation failed: LLM produced no valid questions.")

        return self._finalize_checkpoints(llm_items, concepts)

    def _finalize_checkpoints(
        self,
        raw_items: List[Dict[str, Any]],
        concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validates, normalises, deduplicates, and sorts checkpoints.
        Deduplication: drops any question whose normalised question_text is a
        near-duplicate of an already-accepted question (first character-normalised
        prefix match).
        Sort order: MCQ first, then short/scenario; within type easy→moderate;
        within difficulty by source_timestamp.
        """
        valid_concept_ids = {c["id"] for c in concepts if "id" in c}
        default_concept_id = concepts[0]["id"] if concepts and "id" in concepts[0] else 1

        cleaned = []
        seen_q_texts: set = set()  # for deduplication

        for item in raw_items:
            q_type = str(item.get("question_type", "mcq")).lower().strip()
            if q_type in ["short_answer", "short"]:
                q_type = "short"
            elif q_type == "scenario":
                q_type = "scenario"
            else:
                q_type = "mcq"

            difficulty = str(item.get("difficulty", "easy")).lower().strip()
            if difficulty not in ["easy", "moderate"]:
                difficulty = "easy"

            cid = item.get("concept_id")
            if not cid or cid not in valid_concept_ids:
                cid = default_concept_id

            q_text = str(item.get("question_text", "")).strip()
            if not q_text:
                continue

            # Deduplication: compare normalised 80-character prefix
            q_key = re.sub(r'\s+', ' ', q_text.lower())[:80]
            if q_key in seen_q_texts:
                continue
            seen_q_texts.add(q_key)

            correct = str(item.get("correct_answer", "")).strip()
            if not correct:
                # Must have a correct answer — skip questions the LLM forgot to fill in
                continue

            options = item.get("options") or []
            if q_type == "mcq" and len(options) < 2:
                # Pad to 4 plausible distractors rather than drop the question
                options = [
                    f"A. {correct}",
                    "B. Arbitrary unconstrained behavior",
                    "C. Inverted input/output contract",
                    "D. Preconditions are not enforced",
                ]

            ts = item.get("source_timestamp")
            end_ts = item.get("source_end_timestamp")
            matching_c = next((c for c in concepts if c.get("id") == cid), None)
            if ts is None and matching_c:
                ts = matching_c.get("start_time", 0.0)
            if end_ts is None and matching_c:
                end_ts = matching_c.get("end_time")

            excerpt = item.get("source_excerpt") or ""
            excerpt = str(excerpt).strip() or None

            cleaned.append({
                "concept_id": cid,
                "question_type": q_type,
                "difficulty": difficulty,
                "scenario_text": item.get("scenario_text") if q_type == "scenario" else None,
                "question_text": q_text,
                "options": options if q_type == "mcq" else [],
                "correct_answer": correct,
                "explanation": str(item.get("explanation", "")).strip() or "Verified from lecture content.",
                "source_excerpt": excerpt,
                "source_timestamp": float(ts) if ts is not None else None,
                "source_end_timestamp": float(end_ts) if end_ts is not None else None,
                "target_misconception": item.get("target_misconception"),
                "item_family_role": item.get("item_family_role", "original"),
                "is_review_checkpoint": bool(item.get("is_review_checkpoint", False)),
            })

        def sort_key(q):
            type_rank = 0 if q.get("question_type") == "mcq" else 1
            d_rank = 0 if q.get("difficulty") == "easy" else 1
            return (type_rank, d_rank, q.get("source_timestamp") or 0.0)

        sorted_items = sorted(cleaned, key=sort_key)
        for idx, q in enumerate(sorted_items):
            q["order_index"] = idx

        return sorted_items

    async def _generate_lecture_checkpoints_with_llm(
        self,
        concepts: List[Dict[str, Any]],
        full_transcript: str,
        lecture_title: str
    ) -> List[Dict[str, Any]]:
        """
        Calls the LLM once per concept so the target question count and transcript
        excerpt can be tailored precisely to that concept.

        Per-concept target:
          base = 2 MCQ + 1 short = 3 questions
          +1 per 2 minutes of concept duration, capped at 6
          lecture minimum of 4 questions spread across concepts

        Rate-limit handling:
          On HTTP 429 or transient 5xx, exponential backoff with jitter up to 4
          attempts; on the second+ attempt a smaller/faster model is tried first.
          If a concept batch exhausts all retries it raises RuntimeError.
        """
        # Choose provider + model list
        if self.groq_api_key and self.groq_api_key.strip():
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key.strip()}",
                "Content-Type": "application/json",
            }
            # Ordered by quality; on rate-limit retries we fall back down the list
            models_to_try = [
                "openai/gpt-oss-120b",
                "qwen/qwen3.8-27b",
                "openai/gpt-oss-20b",
            ]
        elif self.api_key and self.api_key.strip():
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key.strip()}",
                "Content-Type": "application/json",
            }
            models_to_try = ["gpt-4o-mini"]
        else:
            raise RuntimeError("Checkpoint generation failed: No AI API key available.")

        LECTURE_MIN = 4   # minimum questions for the whole lecture
        MAX_PER_CONCEPT = 6
        MAX_TRANSCRIPT_CHARS = 3000  # ~750 tokens — well within 8 k TPM limit
        MAX_RETRIES = 4

        num_concepts = len(concepts)
        all_checkpoints: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            for c_idx, concept in enumerate(concepts):
                target = self._target_count_for_concept(concept, LECTURE_MIN, num_concepts)

                # How many MCQ vs short to request
                num_mcq = min(target, 2 + max(0, target - 3))  # 2 base MCQ, extras go to MCQ
                num_short = target - num_mcq  # remainder as short-answer
                # Clamp
                num_mcq = max(2, min(num_mcq, MAX_PER_CONCEPT - 1))
                num_short = max(1, target - num_mcq)

                transcript_excerpt = (concept.get("transcript_text") or "")[:MAX_TRANSCRIPT_CHARS]

                concept_summary = {
                    "concept_id": concept.get("id", c_idx + 1),
                    "title": concept.get("title", ""),
                    "description": concept.get("description", ""),
                    "start_time_seconds": concept.get("start_time", 0.0),
                    "end_time_seconds": concept.get("end_time", 0.0),
                    "core_concepts": concept.get("core_concepts", []),
                    "transcript_excerpt": transcript_excerpt,
                }

                prompt = (
                    f"You are an expert computer science educator writing diagnostic questions for MindTrace.\n"
                    f"Lecture: {lecture_title}\n"
                    f"Concept ({c_idx + 1}/{num_concepts}):\n"
                    f"{json.dumps(concept_summary, indent=2)}\n\n"
                    f"Generate exactly {target} checkpoint questions for THIS concept only:\n"
                    f"  • {num_mcq} multiple-choice questions (question_type: 'mcq')\n"
                    f"  • {num_short} short-answer question(s) (question_type: 'short')\n\n"
                    "Rules — strictly follow all of them:\n"
                    "1. Every question MUST be grounded in the transcript_excerpt above. "
                    "   Do not invent facts not present in the transcript.\n"
                    "2. Each MCQ needs exactly 4 options labelled 'A. ...', 'B. ...', 'C. ...', 'D. ...'.\n"
                    "3. correct_answer for MCQ must be the full option string (e.g. 'A. ...').\n"
                    "4. correct_answer for short-answer must be a concise model answer (1-3 sentences).\n"
                    "5. No two questions may ask the same thing. Vary difficulty: "
                    "   first MCQ easy, second MCQ moderate; first short easy, additional shorts moderate.\n"
                    "6. source_excerpt: a short verbatim quote from the transcript excerpt.\n"
                    "7. source_timestamp: float seconds within "
                    f"[{concept.get('start_time', 0.0)}, {concept.get('end_time', 0.0)}].\n"
                    "8. If the transcript is too short to support the full count, generate fewer — "
                    "   but never invent content.\n\n"
                    "Return ONLY a JSON object: {\"checkpoints\": [...]}"
                )

                concept_success = False
                last_error: Optional[str] = None

                for attempt in range(MAX_RETRIES):
                    model_name = models_to_try[min(attempt, len(models_to_try) - 1)]
                    payload = {
                        "model": model_name,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a professional computer science examiner. "
                                    "Output only valid JSON with no markdown fences."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.3,
                    }

                    try:
                        response = await client.post(url, headers=headers, json=payload)

                        if response.status_code == 200:
                            data = response.json()
                            content = data["choices"][0]["message"]["content"]
                            parsed = json.loads(content)
                            if isinstance(parsed, dict):
                                chks = parsed.get("checkpoints") or []
                            elif isinstance(parsed, list):
                                chks = parsed
                            else:
                                chks = []

                            # Stamp concept_id on every item (LLM sometimes omits it)
                            for q in chks:
                                if not q.get("concept_id"):
                                    q["concept_id"] = concept.get("id", c_idx + 1)

                            if chks:
                                all_checkpoints.extend(chks)
                                concept_success = True
                                break
                            else:
                                last_error = "LLM returned empty checkpoints list"
                                wait = (2 ** attempt) + random.uniform(0.3, 1.0)
                                await asyncio.sleep(wait)

                        elif response.status_code == 429:
                            # Rate limited — exponential backoff with jitter
                            retry_after = None
                            try:
                                retry_after = float(
                                    response.headers.get("retry-after", "")
                                )
                            except (ValueError, TypeError):
                                pass
                            wait = retry_after if retry_after else (
                                (2 ** (attempt + 1)) + random.uniform(1.0, 3.0)
                            )
                            last_error = f"429 rate-limited (wait {wait:.1f}s)"
                            await asyncio.sleep(wait)

                        elif response.status_code in (500, 502, 503, 504):
                            wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                            last_error = f"HTTP {response.status_code}"
                            await asyncio.sleep(wait)

                        else:
                            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                            break  # non-retryable

                    except Exception as exc:
                        last_error = str(exc)
                        wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                        await asyncio.sleep(wait)

                if not concept_success:
                    raise RuntimeError(
                        f"Checkpoint generation failed for concept '{concept.get('title', c_idx)}' "
                        f"after {MAX_RETRIES} attempts. Last error: {last_error}"
                    )

                # Brief inter-concept pause to stay within TPM window
                if c_idx < num_concepts - 1:
                    await asyncio.sleep(1.2)

        return all_checkpoints

    def _generate_extractive_lecture_checkpoints(
        self,
        concepts: List[Dict[str, Any]],
        full_transcript: str = "",
        lecture_title: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Deterministic, content-grounded question generator.
        Extracts genuine questions directly from the concepts and transcript sentences.
        Produces: 4 MCQ (2 easy, 2 mod), 2 Short (1 easy, 1 mod), 2 Scenario (2 mod).
        """
        if not concepts:
            return []

        # Extract sentences from full transcript or concept transcript texts
        all_sentences = []
        for c in concepts:
            t = c.get("transcript_text", "") or ""
            c_start = float(c.get("start_time", 0.0))
            c_end = float(c.get("end_time", c_start + 45.0))
            raw_s_list = [s.strip() for s in re.split(r'(?<=[.!?])\s+', t.strip()) if len(s.strip()) > 15]
            num_s = max(1, len(raw_s_list))
            step = (c_end - c_start) / num_s
            for s_idx, s_clean in enumerate(raw_s_list):
                s_st = round(c_start + s_idx * step, 1)
                s_et = round(min(c_end, s_st + step), 1)
                all_sentences.append((s_clean, c.get("id"), s_st, s_et, c.get("title", "")))

        # Fallback if no transcript text
        if not all_sentences:
            for c in concepts:
                c_start = float(c.get("start_time", 0.0))
                c_end = float(c.get("end_time", c_start + 45.0))
                all_sentences.append((
                    f"{c.get('title', 'Concept')} establishes fundamental rules and operations.",
                    c.get("id"),
                    c_start,
                    c_end,
                    c.get("title", "")
                ))

        c0 = concepts[0]
        c1 = concepts[1] if len(concepts) > 1 else concepts[0]
        c2 = concepts[2] if len(concepts) > 2 else c1
        c_last = concepts[-1]

        questions = []

        # ── 1. MCQ 1 - Easy (Concept 0) ──
        s0_info = all_sentences[0] if all_sentences else (f"{c0.get('title')} defines fundamental mechanisms", c0.get("id"), c0.get("start_time", 0.0), c0.get("end_time", 30.0), c0.get("title"))
        s0_text = s0_info[0].rstrip('.')
        q1 = {
            "concept_id": c0.get("id"),
            "question_type": "mcq",
            "difficulty": "easy",
            "scenario_text": None,
            "question_text": f"According to the lecture, what is the core principle of '{c0.get('title')}'?",
            "options": [
                f"A. {s0_text}",
                "B. The operation occurs randomly without adherence to deterministic rules",
                "C. Inputs and outputs can be interchanged without affecting results",
                "D. The operation is only valid when no arguments are provided"
            ],
            "correct_answer": f"A. {s0_text}",
            "explanation": f"Stated in the lecture discussion of {c0.get('title')}: \"{s0_text}\"",
            "source_excerpt": s0_text,
            "source_timestamp": float(s0_info[2]),
            "source_end_timestamp": float(s0_info[3]),
            "target_misconception": f"Misunderstanding core mechanism of {c0.get('title')}",
            "item_family_role": "original",
            "is_review_checkpoint": False
        }
        questions.append(q1)

        # ── 2. MCQ 2 - Easy (Concept 1) ──
        s1_tuple = all_sentences[min(1, len(all_sentences) - 1)]
        s1_text = s1_tuple[0].rstrip('.')
        q2 = {
            "concept_id": c1.get("id"),
            "question_type": "mcq",
            "difficulty": "easy",
            "scenario_text": None,
            "question_text": f"Which statement accurately reflects the definition taught for '{c1.get('title')}'?",
            "options": [
                f"A. {s1_text}",
                "B. It ignores predefined constraints and accepts arbitrary inputs",
                "C. It permanently mutates memory outside its computational scope",
                "D. It produces inconsistent output values for identical inputs"
            ],
            "correct_answer": f"A. {s1_text}",
            "explanation": f"Directly based on the lecture explanation: \"{s1_text}\"",
            "source_excerpt": s1_text,
            "source_timestamp": float(s1_tuple[2]),
            "source_end_timestamp": float(s1_tuple[3]),
            "target_misconception": f"Superficial recall of {c1.get('title')}",
            "item_family_role": "original",
            "is_review_checkpoint": False
        }
        questions.append(q2)

        # ── 3. Short 1 - Easy (Concept 0) ──
        q3 = {
            "concept_id": c0.get("id"),
            "question_type": "short",
            "difficulty": "easy",
            "scenario_text": None,
            "question_text": f"In your own words, briefly state the primary definition or purpose of '{c0.get('title')}' as explained in this lecture.",
            "options": [],
            "correct_answer": f"{c0.get('title')} defines predictable operations where valid inputs are mapped according to consistent rules without undefined behavior.",
            "explanation": f"Understanding {c0.get('title')} requires identifying its fundamental role and constraints.",
            "source_excerpt": s0_text,
            "source_timestamp": float(s0_info[2]),
            "source_end_timestamp": float(s0_info[3]),
            "target_misconception": f"Inability to articulate definition of {c0.get('title')}",
            "item_family_role": "original",
            "is_review_checkpoint": False
        }
        questions.append(q3)

        # ── 4. MCQ 3 - Moderate (Concept 2 or 1) ──
        s2_tuple = all_sentences[min(2, len(all_sentences) - 1)]
        s2_text = s2_tuple[0].rstrip('.')
        q4 = {
            "concept_id": c2.get("id"),
            "question_type": "mcq",
            "difficulty": "moderate",
            "scenario_text": None,
            "question_text": f"When applying '{c2.get('title')}' in a program, what invariant must strictly hold?",
            "options": [
                "A. Operations must satisfy verified constraints and produce deterministic outputs for given inputs",
                "B. Variables may be rebound arbitrarily without adhering to the declared contract",
                "C. Preconditions can be bypassed if runtime exceptions are ignored",
                "D. Outputs are independent of input parameters and rely solely on global timers"
            ],
            "correct_answer": "A. Operations must satisfy verified constraints and produce deterministic outputs for given inputs",
            "explanation": f"Application of {c2.get('title')} requires verifying input contracts and ensuring deterministic execution.",
            "source_excerpt": s2_text,
            "source_timestamp": float(s2_tuple[2]),
            "source_end_timestamp": float(s2_tuple[3]),
            "target_misconception": f"Failure to verify invariant contracts in {c2.get('title')}",
            "item_family_role": "variant",
            "is_review_checkpoint": True
        }
        questions.append(q4)

        # ── 5. MCQ 4 - Moderate (Concept Last) ──
        c_last_sentences = [s for s in all_sentences if s[1] == c_last.get("id")]
        s_last_tuple = c_last_sentences[0] if c_last_sentences else s2_tuple
        s_last_text = s_last_tuple[0].rstrip('.')
        q5 = {
            "concept_id": c_last.get("id"),
            "question_type": "mcq",
            "difficulty": "moderate",
            "scenario_text": None,
            "question_text": f"What is the expected outcome if input constraints are violated when evaluating '{c_last.get('title')}'?",
            "options": [
                "A. The evaluation becomes undefined or produces an invalid state because inputs lie outside permissible boundaries",
                "B. The system automatically corrects the input values without raising an error",
                "C. The operation succeeds normally because constraints are purely cosmetic recommendations",
                "D. The return value is silently mapped to zero regardless of the rule"
            ],
            "correct_answer": "A. The evaluation becomes undefined or produces an invalid state because inputs lie outside permissible boundaries",
            "explanation": f"Violating input domain boundaries violates the core operational guarantees of {c_last.get('title')}.",
            "source_excerpt": s_last_text,
            "source_timestamp": float(s_last_tuple[2]),
            "source_end_timestamp": float(s_last_tuple[3]),
            "target_misconception": f"Assuming invalid inputs are silently accommodated in {c_last.get('title')}",
            "item_family_role": "variant",
            "is_review_checkpoint": True
        }
        questions.append(q5)

        # ── 6. Short 2 - Moderate (Concept 1) ──
        q6 = {
            "concept_id": c1.get("id"),
            "question_type": "short",
            "difficulty": "moderate",
            "scenario_text": None,
            "question_text": f"Explain why understanding '{c1.get('title')}' is essential when building modular software, and what bug can occur if its constraints are ignored.",
            "options": [],
            "correct_answer": f"It ensures that components interact predictably without hidden side-effects. Ignoring its constraints leads to unexpected mutations, invalid state, or runtime errors.",
            "explanation": f"Modular systems rely on {c1.get('title')} to isolate state and maintain reliable component behavior.",
            "source_excerpt": s1_text,
            "source_timestamp": float(s1_tuple[2]),
            "source_end_timestamp": float(s1_tuple[3]),
            "target_misconception": f"Underestimating impact of side effects in {c1.get('title')}",
            "item_family_role": "variant",
            "is_review_checkpoint": False
        }
        questions.append(q6)

        # ── 7. Scenario 1 - Moderate (Concept 0) ──
        q7 = {
            "concept_id": c0.get("id"),
            "question_type": "scenario",
            "difficulty": "moderate",
            "scenario_text": f"A software engineer writes a core module based on '{c0.get('title')}'. In production testing, edge-case input values occasionally trigger incorrect output because the module does not validate input boundaries.",
            "question_text": f"How should the engineer resolve this issue according to the principles of '{c0.get('title')}' discussed in this lecture?",
            "options": [],
            "correct_answer": "The engineer should enforce explicit validation of input preconditions at the boundary so only permissible values are processed, ensuring predictable and deterministic outputs.",
            "explanation": f"Grounded in {c0.get('title')}: robust systems enforce input boundaries before executing internal transformation rules.",
            "source_excerpt": s0_text,
            "source_timestamp": float(s0_info[2]),
            "source_end_timestamp": float(s0_info[3]),
            "target_misconception": f"Skipping boundary validation in {c0.get('title')}",
            "item_family_role": "variant",
            "is_review_checkpoint": False
        }
        questions.append(q7)

        # ── 8. Scenario 2 - Moderate (Concept Last) ──
        q8 = {
            "concept_id": c_last.get("id"),
            "question_type": "scenario",
            "difficulty": "moderate",
            "scenario_text": f"During a code review, two developers disagree on how to handle state transformations in '{c_last.get('title')}'. One developer suggests modifying a shared external variable, while the other recommends passing explicit arguments and returning a new value.",
            "question_text": f"Which approach aligns with the core principles of '{c_last.get('title')}' taught in this lecture, and why?",
            "options": [],
            "correct_answer": "The approach using explicit arguments and returning a new value is correct because it preserves modularity, avoids hidden side effects, and guarantees deterministic behavior.",
            "explanation": "As emphasized in the lecture, operations should rely strictly on explicit inputs and outputs to prevent side effects.",
            "source_excerpt": s_last_text,
            "source_timestamp": float(s_last_tuple[2]),
            "source_end_timestamp": float(s_last_tuple[3]),
            "target_misconception": f"Relying on hidden mutable state in {c_last.get('title')}",
            "item_family_role": "variant",
            "is_review_checkpoint": False
        }
        questions.append(q8)

        # Sort: All MCQs first (0), then short-answer/open-ended questions at the end (1)
        # Within each question type: Easy first (0), then Moderate (1); within difficulty, sort by source_timestamp
        def sort_key(item):
            type_rank = 0 if item.get("question_type") == "mcq" else 1
            diff_rank = 0 if item.get("difficulty", "easy").lower() == "easy" else 1
            ts = item.get("source_timestamp") or 0.0
            return (type_rank, diff_rank, ts)

        sorted_q = sorted(questions, key=sort_key)
        for idx, q in enumerate(sorted_q):
            q["order_index"] = idx

        return sorted_q

    # ── Legacy support methods (kept for backward-compatibility) ─────────────
    async def generate_item_family_for_concept(
        self,
        concept_title: str,
        concept_description: str,
        transcript_text: str = ""
    ) -> List[Dict[str, Any]]:
        for title_key, q_list in SAMPLE_CONCEPT_CHECKPOINTS.items():
            if title_key.lower() in concept_title.lower() or concept_title.lower() in title_key.lower():
                return self._format_catalog_family(q_list, concept_title)

        if self.api_key and transcript_text and len(transcript_text.strip()) > 20:
            try:
                llm_items = await self._generate_item_family_with_llm(
                    concept_title, concept_description, transcript_text
                )
                if llm_items and len(llm_items) >= 2:
                    return llm_items
            except Exception as e:
                print(f"[CheckpointService] LLM item generation error: {e}. Falling back to extractive engine.")

        return self._generate_extractive_item_family(concept_title, concept_description, transcript_text)

    def _format_catalog_family(self, base_items: List[Dict[str, Any]], concept_title: str) -> List[Dict[str, Any]]:
        first_item = dict(base_items[0])
        first_item["order_index"] = 0
        first_item["difficulty"] = "easy"
        first_item["item_family_role"] = "original"
        first_item["is_review_checkpoint"] = False

        if len(base_items) > 1:
            second_item = dict(base_items[1])
            second_item["order_index"] = 1
            second_item["difficulty"] = "moderate"
            second_item["item_family_role"] = "variant"
            second_item["is_review_checkpoint"] = True
            return [first_item, second_item]

        variant = {
            "question_type": "mcq",
            "difficulty": "moderate",
            "question_text": f"Variant Application: When reasoning about '{concept_title}', which requirement must strictly hold?",
            "options": [
                first_item.get("correct_answer", "The verified invariant"),
                "Arbitrary transformation without constraints",
                "Outputs may vary unpredictably for identical inputs",
                "Preconditions can be skipped during execution"
            ],
            "correct_answer": first_item.get("correct_answer", "The verified invariant"),
            "explanation": f"Grounded in {concept_title}: {first_item.get('explanation', '')}",
            "order_index": 1,
            "is_review_checkpoint": True,
            "item_family_role": "variant",
            "target_misconception": first_item.get("target_misconception", f"Misunderstanding {concept_title}")
        }
        return [first_item, variant]

    def _generate_extractive_item_family(
        self,
        concept_title: str,
        concept_description: str,
        transcript_text: str
    ) -> List[Dict[str, Any]]:
        clean_text = transcript_text.strip()
        if not clean_text or len(clean_text) < 15:
            clean_text = f"{concept_title} establishes foundational definitions and input-output contracts."

        sentences = [
            s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_text)
            if len(s.strip()) > 12
        ]
        if not sentences:
            sentences = [clean_text]

        primary_sentence = sentences[0]
        for s in sentences:
            if any(k in s.lower() for k in ["is ", "means ", "defined ", "refers to ", "crucial", "remember", "rule", "must", "function", "output", "input"]):
                primary_sentence = s
                break

        correct_ans_text = primary_sentence.rstrip('.')
        q1_text = f"According to the lecture discussion of '{concept_title}', which statement is accurate?"
        
        distractor_1 = "The opposite condition is enforced, reversing input and output dependencies."
        distractor_2 = "This behavior occurs randomly without adherence to deterministic rules."
        distractor_3 = "The operation operates independently of parameters and ignores constraints."

        options_q1 = [
            f"A. {correct_ans_text}",
            f"B. {distractor_1}",
            f"C. {distractor_2}",
            f"D. {distractor_3}"
        ]

        item_1 = {
            "question_type": "mcq",
            "difficulty": "easy",
            "question_text": q1_text,
            "options": options_q1,
            "correct_answer": f"A. {correct_ans_text}",
            "explanation": f"Directly stated in the lecture: \"{primary_sentence}\"",
            "order_index": 0,
            "is_review_checkpoint": False,
            "item_family_role": "original",
            "target_misconception": f"Misunderstanding core mechanism of {concept_title}",
            "source_excerpt": primary_sentence,
            "source_timestamp": 0.0
        }

        secondary_sentence = sentences[1] if len(sentences) > 1 else sentences[0]
        if len(sentences) > 2 and secondary_sentence == primary_sentence:
            secondary_sentence = sentences[2]

        sec_text = secondary_sentence.rstrip('.')
        q2_text = f"Follow-up Variant: Regarding '{concept_title}', which of the following principles is established in this lecture?"
        options_q2 = [
            f"A. {sec_text}",
            "B. The principle only applies when variable names match textbook conventions exactly.",
            "C. Constraints can be relaxed whenever inputs exceed boundary limits.",
            "D. No predictable mapping exists across different execution environments."
        ]

        item_2 = {
            "question_type": "mcq",
            "difficulty": "moderate",
            "question_text": q2_text,
            "options": options_q2,
            "correct_answer": f"A. {sec_text}",
            "explanation": f"As explained by the instructor: \"{secondary_sentence}\"",
            "order_index": 1,
            "is_review_checkpoint": True,
            "item_family_role": "variant",
            "target_misconception": f"Superficial pattern-matching without conceptual understanding of {concept_title}",
            "source_excerpt": secondary_sentence,
            "source_timestamp": 0.0
        }

        return [item_1, item_2]

    async def _generate_item_family_with_llm(
        self,
        concept_title: str,
        concept_description: str,
        transcript_text: str
    ) -> List[Dict[str, Any]]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        prompt = (
            "You are an expert psychometrician and computer science educator designing diagnostic questions for MindTrace.\n"
            f"Concept Title: {concept_title}\n"
            f"Concept Description: {concept_description}\n"
            f"Transcript Excerpt: {transcript_text[:900]}\n\n"
            "Task:\n"
            "1. Ground questions strictly in what the instructor says in the transcript excerpt.\n"
            "2. Generate an 'Item Family' of 2-3 diagnostic multiple-choice questions (4 options: A, B, C, D each):\n"
            "   - Item 1 (original): Tests key knowledge explained in the excerpt. Incorrect options reflect plausible misconceptions.\n"
            "     item_family_role='original', is_review_checkpoint=false, order_index=0, difficulty='easy'.\n"
            "   - Item 2 (variant): An ISOMORPHIC variant testing the identical underlying mechanism with changed surface wording.\n"
            "     item_family_role='variant', is_review_checkpoint=true, order_index=1, difficulty='moderate'.\n"
            "   - Item 3 (transfer): A NEAR-TRANSFER item testing transfer to a concrete application/boundary.\n"
            "     item_family_role='transfer', is_review_checkpoint=true, order_index=2, difficulty='moderate'.\n\n"
            "Output JSON with key 'checkpoints' as a list of items with keys:\n"
            "question_type, difficulty, question_text, options, correct_answer, explanation, order_index, is_review_checkpoint, item_family_role, target_misconception, source_excerpt."
        )

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.25
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "checkpoints" in parsed:
                    return parsed["checkpoints"]
                elif isinstance(parsed, list):
                    return parsed
        return []


checkpoint_service = CheckpointService()
