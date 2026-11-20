import json
import httpx
import re
import asyncio
import random
import difflib
import time
from typing import List, Dict, Any, Optional, Callable
from app.config import settings

# ── CHECKPOINT GENERATION CONFIGURATION CONSTANTS ─────────────────────────────
MIN_QUESTIONS_PER_CONCEPT = 3        # Minimum questions per concept (1 easy, 1 mod, 1 hard)
MAX_QUESTIONS_PER_CONCEPT = 9        # Tighter cap per concept (6-9 max)
WORDS_PER_QUESTION = 40              # Scaling factor: roughly 1 question per 40 transcript words
MAX_MCQ_PER_DIFFICULTY = 2           # Up to 2 MCQs per difficulty level
MAX_SHORT_PER_DIFFICULTY = 3         # Up to 3 short-answer questions per difficulty level
DIFFICULTY_LEVELS = ["easy", "moderate", "hard"]
QUESTION_SIMILARITY_THRESHOLD = 0.72  # Similarity cutoff to drop near-duplicate questions
CONCURRENT_CONCEPT_WORKERS = 1       # Process concepts sequentially to respect Groq TPM rate limits


def calculate_concept_target_distribution(transcript_text: str) -> Dict[str, Any]:
    """
    Calculates target question counts per difficulty and question type
    scaled to the transcript length (roughly 1 question per 40 words,
    minimum 3 per concept, maximum 9 per concept).
    Ensures a 45-word concept gets 3 questions (not 4),
    and a 500-word concept gets all 9 questions.
    Splits the target between MCQ and Short Answer at each difficulty level.
    Hard questions are ALWAYS short answer (application scenarios).
    """
    words = len(transcript_text.strip().split()) if transcript_text else 0
    if words < 60:
        total_target = MIN_QUESTIONS_PER_CONCEPT  # 3 questions
    elif words < 120:
        total_target = 4
    elif words < 200:
        total_target = 5
    elif words < 300:
        total_target = 6
    elif words < 400:
        total_target = 7
    elif words < 480:
        total_target = 8
    else:
        total_target = MAX_QUESTIONS_PER_CONCEPT  # 9 questions

    total_target = max(MIN_QUESTIONS_PER_CONCEPT, min(total_target, MAX_QUESTIONS_PER_CONCEPT))

    # Distribute total questions evenly across easy, moderate, hard
    base_per_diff = total_target // 3
    remainder = total_target % 3

    distribution = {}
    for idx, diff in enumerate(DIFFICULTY_LEVELS):
        diff_count = base_per_diff + (1 if idx < remainder else 0)

        if diff == "easy":
            # Recall of stated facts: split between MCQ and Short Answer
            if diff_count <= 1:
                mcq_count = 1
                short_count = 0
            elif diff_count == 2:
                mcq_count = 1
                short_count = 1
            else:  # 3
                mcq_count = 2
                short_count = 1
        elif diff == "moderate":
            # Explain / compare mechanisms: split between MCQ and Short Answer
            if diff_count <= 1:
                mcq_count = 0
                short_count = 1
            elif diff_count == 2:
                mcq_count = 1
                short_count = 1
            else:  # 3
                mcq_count = 1
                short_count = 2
        else:  # hard
            # Apply ideas to new scenarios: ALL hard questions are short answer (application scenarios)
            mcq_count = 0
            short_count = diff_count

        distribution[diff] = {
            "total": diff_count,
            "mcq": mcq_count,
            "short": short_count
        }

    return {
        "total_target": total_target,
        "word_count": words,
        "difficulties": distribution
    }


def filter_unique_concept_questions(
    raw_questions: List[Dict[str, Any]],
    similarity_threshold: float = QUESTION_SIMILARITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Drops duplicate and near-duplicate questions using SequenceMatcher ratio
    and token Jaccard similarity.
    """
    unique = []
    seen_texts = []

    for q in raw_questions:
        q_text = str(q.get("question_text") or q.get("question") or "").strip()
        if not q_text:
            continue

        norm_q = re.sub(r'[^\w\s]', '', q_text.lower()).strip()
        if not norm_q:
            continue

        is_dup = False
        for prev_text, prev_norm in seen_texts:
            if norm_q == prev_norm:
                is_dup = True
                break
            ratio = difflib.SequenceMatcher(None, norm_q, prev_norm).ratio()
            if ratio >= similarity_threshold:
                is_dup = True
                break
            tokens1 = set(norm_q.split())
            tokens2 = set(prev_norm.split())
            if tokens1 and tokens2:
                jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)
                if jaccard >= 0.80:
                    is_dup = True
                    break

        if not is_dup:
            seen_texts.append((q_text, norm_q))
            unique.append(q)
        else:
            print(f"[checkpoint_service] Dropped duplicate/near-duplicate question: '{q_text[:60]}...'")

    return unique

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

    async def generate_lecture_checkpoints(
        self,
        concepts: List[Dict[str, Any]],
        full_transcript: str = "",
        lecture_title: str = "",
        on_concept_ready: Optional[Callable[[int, List[Dict[str, Any]]], Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates diagnostic checkpoint questions per concept with:
          • Up to 3 MCQ and 3 short-answer questions per difficulty (easy, moderate, hard)
          • Scaled down for short transcripts (roughly 1 question per 15-20 words, min 3, max 18 per concept)
          • Processed 2-3 concepts in parallel using asyncio semaphore and 429 retry backoff
          • One LLM call per concept returning all difficulties as validated JSON
          • Similarity check dropping duplicates and near-duplicates
          • Progressive DB save via on_concept_ready callback as soon as each concept finishes
        """
        if not concepts:
            return []

        has_api_key = bool(
            (self.groq_api_key and self.groq_api_key.strip()) or
            (self.api_key and self.api_key.strip())
        )
        if not has_api_key:
            raise RuntimeError("Checkpoint generation failed: No AI API key configured.")

        # Choose provider + model list
        if self.groq_api_key and self.groq_api_key.strip():
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key.strip()}",
                "Content-Type": "application/json",
            }
            models_to_try = [
                "openai/gpt-oss-20b",
                "openai/gpt-oss-120b",
                "qwen/qwen3.8-27b",
            ]
        else:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key.strip()}",
                "Content-Type": "application/json",
            }
            models_to_try = ["gpt-4o-mini"]

        MAX_TRANSCRIPT_CHARS = 3500
        MAX_RETRIES = 6
        sem = asyncio.Semaphore(CONCURRENT_CONCEPT_WORKERS)
        all_concept_results: List[List[Dict[str, Any]]] = [[] for _ in concepts]

        async with httpx.AsyncClient(timeout=120.0) as client:
            async def process_single_concept(c_idx: int, concept: Dict[str, Any]):
                transcript_text = (concept.get("transcript_text") or "").strip()
                transcript_excerpt = transcript_text[:MAX_TRANSCRIPT_CHARS]
                duration = float(concept.get("end_time", 0)) - float(concept.get("start_time", 0))

                dist = calculate_concept_target_distribution(transcript_text)
                target_total = dist["total_target"]
                diffs = dist["difficulties"]

                if dist["word_count"] < 40 or duration < 20.0:
                    print(
                        f"[checkpoint_service] Concept '{concept.get('title')}' (id={concept.get('id')}): "
                        f"Transcript segment is short ({dist['word_count']} words, {duration:.1f}s); "
                        f"target scaled to {target_total} questions.",
                        flush=True
                    )

                concept_summary = {
                    "concept_id": concept.get("id", c_idx + 1),
                    "title": concept.get("title", ""),
                    "description": concept.get("description", ""),
                    "start_time_seconds": concept.get("start_time", 0.0),
                    "end_time_seconds": concept.get("end_time", 0.0),
                    "core_concepts": concept.get("core_concepts", []),
                    "transcript_excerpt": transcript_excerpt,
                }

                # Build the question breakdown lines
                easy_line = (
                    f"EASY: {diffs['easy']['total']} questions "
                    f"({diffs['easy']['mcq']} MCQ, {diffs['easy']['short']} Short Answer) - "
                    "direct factual recall of terms, definitions, and rules stated in the transcript."
                )
                mod_line = (
                    f"MODERATE: {diffs['moderate']['total']} questions "
                    f"({diffs['moderate']['mcq']} MCQ, {diffs['moderate']['short']} Short Answer) - "
                    "explain mechanisms, compare concepts, or explain why/how principles operate."
                )
                hard_line = (
                    f"HARD: {diffs['hard']['total']} questions "
                    f"({diffs['hard']['mcq']} MCQ, {diffs['hard']['short']} Short Answer) - "
                    "apply concept to realistic programming or system scenarios answerable from lecture principles."
                )

                mcq_example = json.dumps({
                    "question_type": "mcq",
                    "difficulty": "easy",
                    "question_text": "What does LIFO stand for?",
                    "options": ["A. Last In, First Out", "B. First In, Last Out", "C. Last In, First Off", "D. Least In, Furthest Out"],
                    "correct_answer": "A. Last In, First Out",
                    "explanation": "LIFO means the last element pushed is the first to be popped.",
                    "source_excerpt": "A stack uses LIFO ordering",
                    "source_timestamp": 2.5
                }, indent=2)

                short_example = json.dumps({
                    "question_type": "short",
                    "difficulty": "hard",
                    "question_text": "Describe how you would use a stack to check balanced parentheses.",
                    "options": [],
                    "correct_answer": "Push each opening bracket onto the stack; pop when a closing bracket is found; return balanced if stack is empty at end.",
                    "explanation": "This applies the LIFO property to track nesting.",
                    "source_excerpt": "stacks are used in many algorithms",
                    "source_timestamp": 10.0
                }, indent=2)

                prompt = (
                    f"You are an expert computer science educator and test author for MindTrace.\n"
                    f"Lecture Title: {lecture_title}\n"
                    f"Target Concept ({c_idx + 1}/{len(concepts)}):\n"
                    f"{json.dumps(concept_summary, indent=2)}\n\n"
                    "TASK: Generate diagnostic checkpoint questions for THIS concept, strictly grounded in its transcript excerpt.\n\n"
                    f"Generate exactly {target_total} distinct questions distributed as follows:\n"
                    f"- {easy_line}\n"
                    f"- {mod_line}\n"
                    f"- {hard_line}\n\n"
                    "RULES:\n"
                    "1. question_type must be exactly the string \"mcq\" for multiple-choice or \"short\" for short-answer.\n"
                    "2. For MCQ: provide exactly 4 items in \"options\" (e.g. \"A. ...\"). \"correct_answer\" must match one option exactly.\n"
                    "3. For short-answer: \"options\" must be an empty array []. \"correct_answer\" must be a concise model answer.\n"
                    "4. Hard questions MUST use question_type \"short\" and present a realistic application scenario.\n"
                    "5. Every question must be answerable solely from the transcript excerpt above. No placeholders.\n"
                    "6. Every question must have a non-empty correct_answer.\n"
                    "7. difficulty must be exactly \"easy\", \"moderate\", or \"hard\".\n"
                    "8. Avoid duplicates or near-duplicate questions.\n"
                    f"9. source_timestamp must be a float between {concept.get('start_time', 0.0)} and {concept.get('end_time', 0.0)}.\n\n"
                    "EXAMPLE MCQ:\n"
                    f"{mcq_example}\n\n"
                    "EXAMPLE SHORT ANSWER:\n"
                    f"{short_example}\n\n"
                    "Return ONLY a valid JSON object in this exact format:\n"
                    "{\"checkpoints\": [ ...list of question objects... ]}"
                )

                concept_success = False
                last_error: Optional[str] = None
                raw_chks: List[Dict[str, Any]] = []
                t_concept_start = time.perf_counter()
                t_backoff_total = 0.0

                async with sem:
                    attempt = 0
                    rate_limit_hits = 0
                    MAX_RATE_LIMIT_RETRIES = 8
                    use_json_format = True

                    while attempt < MAX_RETRIES and rate_limit_hits < MAX_RATE_LIMIT_RETRIES:
                        model_name = models_to_try[min(attempt, len(models_to_try) - 1)]
                        payload = {
                            "model": model_name,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are a professional computer science examiner. Output only valid JSON with no markdown fences."
                                },
                                {"role": "user", "content": prompt},
                            ],
                            "max_tokens": 4096,
                            "temperature": 0.25,
                        }
                        if use_json_format:
                            payload["response_format"] = {"type": "json_object"}

                        try:
                            response = await client.post(url, headers=headers, json=payload)

                            if response.status_code == 200:
                                data = response.json()
                                content = data["choices"][0]["message"]["content"]
                                # Strip markdown code fences if any
                                content = re.sub(r'^```(?:json)?\s*', '', content.strip(), flags=re.MULTILINE)
                                content = re.sub(r'```\s*$', '', content.strip(), flags=re.MULTILINE)
                                content = content.strip()
                                try:
                                    parsed = json.loads(content)
                                except json.JSONDecodeError:
                                    # Try extracting first JSON object from text
                                    m = re.search(r'\{[\s\S]*\}', content)
                                    parsed = json.loads(m.group()) if m else {}
                                if isinstance(parsed, dict):
                                    raw_chks = (
                                        parsed.get("checkpoints")
                                        or parsed.get("questions")
                                        or parsed.get("items")
                                        or parsed.get("data")
                                        or []
                                    )
                                    if not raw_chks and len(parsed) == 1:
                                        first_val = next(iter(parsed.values()))
                                        if isinstance(first_val, list):
                                            raw_chks = first_val
                                elif isinstance(parsed, list):
                                    raw_chks = parsed
                                else:
                                    raw_chks = []

                                if raw_chks:
                                    concept_success = True
                                    break
                                else:
                                    last_error = "LLM returned empty checkpoints list"
                                    attempt += 1
                                    wait = (2 ** attempt) + random.uniform(0.3, 1.0)
                                    await asyncio.sleep(wait)

                            elif response.status_code == 400 and use_json_format:
                                # json_object mode was rejected (json_validate_failed) — retry without it on SAME model
                                last_error = f"HTTP 400 json_validate_failed; retrying without response_format"
                                print(f"[checkpoint_service] HTTP 400 on '{concept.get('title')}', retrying without json_object constraint...", flush=True)
                                use_json_format = False
                                await asyncio.sleep(1.0)
                                # do not increment attempt so same model is retried without json constraint

                            elif response.status_code == 429:
                                rate_limit_hits += 1
                                retry_after = None
                                try:
                                    retry_after = float(response.headers.get("retry-after", ""))
                                except (ValueError, TypeError):
                                    pass
                                wait = retry_after if retry_after else (
                                    (2 ** min(rate_limit_hits, 4)) + random.uniform(2.0, 5.0)
                                )
                                t_backoff_total += wait
                                last_error = f"429 rate-limited (wait {wait:.1f}s)"
                                print(f"[checkpoint_service] 429 on concept '{concept.get('title')}' (hit {rate_limit_hits}/{MAX_RATE_LIMIT_RETRIES}), backing off {wait:.1f}s...", flush=True)
                                await asyncio.sleep(wait)
                                # do not increment attempt, retry after rate limit resets

                            elif response.status_code in (500, 502, 503, 504):
                                attempt += 1
                                wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                                last_error = f"HTTP {response.status_code}"
                                await asyncio.sleep(wait)

                            else:
                                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                                attempt += 1
                                break

                        except Exception as exc:
                            last_error = str(exc)
                            attempt += 1
                            wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                            await asyncio.sleep(wait)

                if not concept_success or not raw_chks:
                    print(
                        f"[checkpoint_service] Warning: LLM failed for concept '{concept.get('title')}' "
                        f"after {MAX_RETRIES} attempts ({last_error}).",
                        flush=True
                    )
                    return []

                # Stamp concept_id on all raw items
                for q in raw_chks:
                    q["concept_id"] = concept.get("id", c_idx + 1)

                # Similarity check: filter out duplicates and near-duplicates
                unique_chks = filter_unique_concept_questions(raw_chks, QUESTION_SIMILARITY_THRESHOLD)

                # Finalize, normalize, and sort this concept's questions in easy -> moderate -> hard order
                concept_final = self._finalize_single_concept_checkpoints(unique_chks, concept)

                # Ensure required hard questions are present (fix for concept 326 / complex concepts)
                hard_count = sum(1 for q in concept_final if q.get("difficulty") == "hard")
                target_hard = diffs["hard"]["total"]
                if hard_count < target_hard and target_hard > 0:
                    needed_hard = target_hard - hard_count
                    print(
                        f"[checkpoint_service] Concept '{concept.get('title')}' has {hard_count}/{target_hard} hard questions. "
                        f"Generating {needed_hard} targeted hard scenario question(s)...",
                        flush=True
                    )
                    supp_hard = await self._generate_targeted_hard_questions(
                        client=client,
                        url=url,
                        headers=headers,
                        models_to_try=models_to_try,
                        concept=concept,
                        lecture_title=lecture_title,
                        count=needed_hard,
                        sem=sem
                    )
                    if supp_hard:
                        for sq in supp_hard:
                            sq["concept_id"] = concept.get("id", c_idx + 1)
                        merged_items = raw_chks + supp_hard
                        unique_chks = filter_unique_concept_questions(merged_items, QUESTION_SIMILARITY_THRESHOLD)
                        concept_final = self._finalize_single_concept_checkpoints(unique_chks, concept)

                # Log per-concept timing and 429 backoff breakdown
                t_concept_elapsed = time.perf_counter() - t_concept_start
                diff_tally = {"easy": 0, "moderate": 0, "hard": 0}
                type_tally = {"mcq": 0, "short": 0}
                for q in concept_final:
                    diff_tally[q.get("difficulty", "easy")] = diff_tally.get(q.get("difficulty", "easy"), 0) + 1
                    type_tally[q.get("question_type", "mcq")] = type_tally.get(q.get("question_type", "mcq"), 0) + 1

                print(
                    f"[checkpoint_service] Concept '{concept.get('title')}' (id={concept.get('id')}): "
                    f"completed in {t_concept_elapsed:.2f}s ({t_backoff_total:.2f}s spent in 429 backoff). "
                    f"Questions: {len(concept_final)} | Difficulties: {diff_tally} | Types: {type_tally}",
                    flush=True
                )

                # PROGRESSIVE DB COMMIT: Save as soon as this concept is done!
                if on_concept_ready and concept_final:
                    try:
                        res = on_concept_ready(concept.get("id"), concept_final)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as cb_err:
                        print(f"[checkpoint_service] Progressive DB save callback error for concept {concept.get('id')}: {cb_err}", flush=True)

                all_concept_results[c_idx] = concept_final
                return concept_final

            # Run 2-3 concepts in parallel with semaphore
            tasks = [process_single_concept(i, c) for i, c in enumerate(concepts)]
            await asyncio.gather(*tasks)

        # Flatten and assign global sequential order_index across the lecture
        all_flattened = []
        for c_questions in all_concept_results:
            all_flattened.extend(c_questions)

        for global_idx, q in enumerate(all_flattened):
            q["order_index"] = global_idx

        return all_flattened

    async def _generate_targeted_hard_questions(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str],
        models_to_try: List[str],
        concept: Dict[str, Any],
        lecture_title: str,
        count: int = 1,
        sem: Optional[asyncio.Semaphore] = None
    ) -> List[Dict[str, Any]]:
        """
        Targeted fallback generator for missing hard application scenario questions.
        Asks specifically for scenario-based short-answer questions grounded in the transcript.
        """
        excerpt = (concept.get("transcript_text") or "")[:3000]
        title = concept.get("title", "")
        start_ts = concept.get("start_time", 0.0)
        end_ts = concept.get("end_time", 0.0)

        prompt = (
            f"You are a computer science examiner for MindTrace.\n"
            f"Lecture: {lecture_title}\n"
            f"Concept: {title}\n"
            f"Transcript Segment:\n{excerpt}\n\n"
            f"TASK: Generate exactly {count} HARD application scenario question(s) for this concept.\n"
            "RULES:\n"
            "1. difficulty must be \"hard\".\n"
            "2. question_type must be \"short\".\n"
            "3. options must be an empty list [].\n"
            "4. Question must present a concrete realistic scenario/problem and ask the student to apply the concept.\n"
            "5. correct_answer must be a clear, concise model answer based strictly on the transcript principles.\n"
            f"6. source_timestamp must be a float between {start_ts} and {end_ts}.\n\n"
            "Return ONLY valid JSON in this format:\n"
            '{"checkpoints": [{"question_type": "short", "difficulty": "hard", "scenario_text": "...", "question_text": "...", "options": [], "correct_answer": "...", "explanation": "...", "source_timestamp": ' + str(start_ts) + '}]}'
        )

        for attempt in range(3):
            model_name = models_to_try[attempt % len(models_to_try)]
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a professional computer science examiner. Output only valid JSON with no markdown fences."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.25,
                "response_format": {"type": "json_object"}
            }
            try:
                if sem:
                    async with sem:
                        resp = await client.post(url, headers=headers, json=payload)
                else:
                    resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"].strip()
                    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
                    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE).strip()
                    parsed = json.loads(text)
                    items = parsed.get("checkpoints") or parsed.get("questions") or []
                    if items:
                        for it in items:
                            it["difficulty"] = "hard"
                            it["question_type"] = "short"
                            it["options"] = []
                            if not it.get("scenario_text"):
                                it["scenario_text"] = f"Scenario Application for {title}"
                        print(f"[checkpoint_service] Successfully generated {len(items)} supplementary hard question(s) for '{title}'.", flush=True)
                        return items
                elif resp.status_code == 429:
                    await asyncio.sleep(4.0 * (attempt + 1))
            except Exception as e:
                print(f"[checkpoint_service] Supplementary hard question attempt {attempt+1} failed: {e}", flush=True)
                await asyncio.sleep(2.0)

        return []

    def _finalize_single_concept_checkpoints(
        self,
        raw_items: List[Dict[str, Any]],
        concept: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Validates and normalizes checkpoints for a single concept.
        Sorts strictly in easy -> moderate -> hard order.
        """
        cid = concept.get("id", 1)
        cleaned = []

        diff_map = {
            "easy": "easy",
            "moderate": "moderate",
            "medium": "moderate",
            "mod": "moderate",
            "hard": "hard",
            "difficult": "hard",
            "advanced": "hard",
        }

        for item in raw_items:
            raw_type = str(
                item.get("question_type") or
                item.get("type") or
                item.get("format") or
                ""
            ).lower().strip()

            options = item.get("options") or item.get("choices") or []

            if raw_type in ["short_answer", "short", "scenario", "free_response", "text"]:
                q_type = "short"
            elif raw_type in ["mcq", "multiple_choice", "multiple-choice"]:
                q_type = "mcq"
            else:
                q_type = "mcq" if (options and len(options) >= 2) else "short"

            raw_diff = str(item.get("difficulty", "easy")).lower().strip()
            difficulty = diff_map.get(raw_diff, "easy")

            # Hard questions should be short answer (application scenarios)
            if difficulty == "hard" and q_type == "mcq" and not (options and len(options) >= 2):
                q_type = "short"

            q_text = str(item.get("question_text") or item.get("question") or "").strip()
            if not q_text:
                continue

            correct = str(item.get("correct_answer") or item.get("answer") or "").strip()
            if not correct:
                continue  # Never pad without correct answer

            if q_type == "short":
                options = []
            elif q_type == "mcq":
                if len(options) < 2:
                    options = [
                        f"A. {correct}",
                        "B. Inverted input/output contract",
                        "C. Arbitrary unconstrained behavior",
                        "D. Preconditions are not enforced",
                    ]
                else:
                    options = [str(opt).strip() for opt in options if str(opt).strip()]

            ts = item.get("source_timestamp")
            end_ts = item.get("source_end_timestamp")
            if ts is None:
                ts = concept.get("start_time", 0.0)
            if end_ts is None:
                end_ts = concept.get("end_time")

            excerpt = item.get("source_excerpt") or ""
            excerpt = str(excerpt).strip() or None

            scenario = item.get("scenario_text") or item.get("scenario")
            if not scenario and difficulty == "hard":
                scenario = f"Application Scenario for {concept.get('title', 'Concept')}"

            cleaned.append({
                "concept_id": cid,
                "question_type": q_type,
                "difficulty": difficulty,
                "scenario_text": scenario if q_type == "short" and difficulty == "hard" else None,
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

        diff_weights = {"easy": 0, "moderate": 1, "hard": 2}
        type_weights = {"mcq": 0, "short": 1}

        # Sort: easy -> moderate -> hard; within difficulty: MCQs first, then Short; then timestamp
        def sort_key(q):
            d_rank = diff_weights.get(q.get("difficulty", "easy"), 0)
            t_rank = type_weights.get(q.get("question_type", "mcq"), 0)
            ts = q.get("source_timestamp") or 0.0
            return (d_rank, t_rank, ts)

        sorted_items = sorted(cleaned, key=sort_key)
        for idx, q in enumerate(sorted_items):
            q["order_index"] = idx

        return sorted_items

    def _finalize_checkpoints(
        self,
        raw_items: List[Dict[str, Any]],
        concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Backward-compatible wrapper for static/catalog checkpoints.
        """
        concept_map = {c.get("id"): c for c in concepts}
        items_by_concept: Dict[int, List[Dict[str, Any]]] = {}
        for item in raw_items:
            cid = item.get("concept_id", concepts[0]["id"] if concepts else 1)
            items_by_concept.setdefault(cid, []).append(item)

        all_final = []
        for c in concepts:
            cid = c.get("id", 1)
            c_items = items_by_concept.get(cid, [])
            if c_items:
                all_final.extend(self._finalize_single_concept_checkpoints(c_items, c))

        for idx, q in enumerate(all_final):
            q["order_index"] = idx
        return all_final

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
