import json
import re
import uuid
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.config import settings
from app.models.all_models import Assessment, Lecture, Concept, Checkpoint, Transcript


DIFFICULTY_GUIDELINES = {
    "easy": {
        "title": "Easy Assessment",
        "description": "Tests fundamental knowledge, definitions, and basic understanding from the lecture.",
        "focus": (
            "Focus on direct factual recall of terms, core definitions, and foundational principles explicitly stated in the transcript. "
            "Use clear, straightforward wording and simple illustrative examples."
        ),
        "mcq_style": "Test recognition of key terminology, direct properties, and fundamental definitions.",
        "short_style": "Ask the student to state or describe a foundational concept in their own words, giving a basic example."
    },
    "moderate": {
        "title": "Moderate Assessment",
        "description": "Tests conceptual mechanisms, comparing related ideas, and practical applications.",
        "focus": (
            "Focus on explaining mechanisms, comparing and contrasting related concepts, and explaining why or how principles operate. "
            "Questions should require reasoning beyond simple recall."
        ),
        "mcq_style": "Test distinguishing between related ideas, identifying why a particular rule applies, or predicting behavior under standard conditions.",
        "short_style": "Ask the student to explain the mechanism behind a concept, compare it with an alternative, or explain why a particular approach works."
    },
    "hard": {
        "title": "Hard Assessment",
        "description": "Tests advanced understanding, complex scenarios, edge cases, and problem-solving.",
        "focus": (
            "Focus on multi-step reasoning, real-world scenario analysis, edge cases, debugging conceptual pitfalls, and synthesizing multiple principles from the lecture.",
        ),
        "mcq_style": "Present a realistic scenario, trade-off, or failure condition and ask the student to identify the correct diagnosis, consequence, or optimal resolution.",
        "short_style": "Present a complex application scenario or system design dilemma and ask the student to design, analyze, or troubleshoot the solution using lecture principles."
    }
}


class AssessmentGenerationService:
    def __init__(self):
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", "")
        self.api_key = getattr(settings, "OPENAI_API_KEY", "")

    async def get_or_create_assessment(
        self,
        db: Session,
        lecture_id: int,
        difficulty: str,
        force_fresh: bool = False
    ) -> Assessment:
        """
        Retrieves existing assessment for (lecture_id, difficulty) or generates a fresh one.
        If force_fresh=True (for retakes), generates a new set of questions excluding questions
        from previous attempts/assessments to avoid repeating questions.
        Guarantees 4 MCQs + 3 Short Answer questions = 7 questions total.
        """
        difficulty = difficulty.lower().strip()
        if difficulty not in ("easy", "moderate", "hard"):
            raise HTTPException(status_code=400, detail=f"Invalid difficulty '{difficulty}'. Choose 'easy', 'moderate', or 'hard'.")

        diff_meta = DIFFICULTY_GUIDELINES.get(difficulty, DIFFICULTY_GUIDELINES["moderate"])

        # 1. If not forcing fresh generation, check if an assessment already exists
        if not force_fresh:
            existing = db.query(Assessment).filter(
                Assessment.lecture_id == lecture_id,
                Assessment.difficulty == difficulty
            ).order_by(Assessment.id.desc()).first()

            if existing and existing.questions and len(existing.questions) == 7:
                return existing

        # 2. Fetch lecture, concepts, transcript
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        if not lecture:
            raise HTTPException(status_code=404, detail=f"Lecture {lecture_id} not found.")

        concepts = db.query(Concept).filter(Concept.lecture_id == lecture_id).order_by(Concept.start_time.asc()).all()
        transcript = db.query(Transcript).filter(Transcript.lecture_id == lecture_id).first()
        full_transcript = (transcript.full_text if transcript and transcript.full_text else "").strip()

        # Check sufficiency
        if not concepts and len(full_transcript.split()) < 30:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient lecture content to generate a 7-question {difficulty} assessment. The lecture needs at least one processed concept and transcript."
            )

        # 3. Collect all existing questions across assessments to prevent repeating questions
        all_prior = db.query(Assessment).filter(
            Assessment.lecture_id == lecture_id
        ).all()

        excluded_questions = []
        for prior in all_prior:
            for q in prior.questions:
                q_text = q.get("question_text", "").strip()
                if q_text:
                    excluded_questions.append(f"[{prior.difficulty.upper()}] {q_text}")

        same_diff_count = db.query(Assessment).filter(
            Assessment.lecture_id == lecture_id,
            Assessment.difficulty == difficulty
        ).count()
        attempt_label = f" (Attempt {same_diff_count + 1})" if same_diff_count > 0 else ""

        # 4. Generate the 7 fresh questions
        generated_questions = await self._generate_assessment_questions(
            lecture=lecture,
            concepts=concepts,
            full_transcript=full_transcript,
            difficulty=difficulty,
            excluded_questions=excluded_questions,
            seed_offset=same_diff_count
        )

        new_assessment = Assessment(
            lecture_id=lecture_id,
            difficulty=difficulty,
            title=f"{lecture.title} - {diff_meta['title']}{attempt_label}",
            description=diff_meta["description"],
            questions=generated_questions
        )
        db.add(new_assessment)
        db.commit()
        db.refresh(new_assessment)
        return new_assessment

    async def _generate_assessment_questions(
        self,
        lecture: Lecture,
        concepts: List[Concept],
        full_transcript: str,
        difficulty: str,
        excluded_questions: List[str],
        seed_offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Generates exactly 4 MCQs and 3 Short Answer questions using Groq / OpenAI.
        """
        diff_info = DIFFICULTY_GUIDELINES.get(difficulty, DIFFICULTY_GUIDELINES["moderate"])

        # Prepare concept summaries
        concept_list = []
        for c in concepts:
            concept_list.append({
                "concept_id": c.id,
                "title": c.title,
                "description": c.description or "",
                "start_time": float(c.start_time or 0.0),
                "end_time": float(c.end_time or 0.0)
            })

        # Transcript excerpt (limit to ~3500 chars to balance speed, token consumption, and rich grounding)
        transcript_excerpt = full_transcript[:3500] if full_transcript else "Transcript unavailable."

        excluded_block = ""
        if excluded_questions:
            excluded_block = (
                "DO NOT REPEAT OR CLOSELY REPHRASE ANY OF THE FOLLOWING QUESTIONS ALREADY USED IN OTHER ASSESSMENTS:\n"
                + "\n".join(f"- {eq}" for eq in excluded_questions[:15])
                + "\n\n"
            )

        prompt = f"""You are an expert university professor creating an authoritative, rigorous assessment for the following lecture.

LECTURE TITLE: {lecture.title}
DIFFICULTY LEVEL: {difficulty.upper()}
DIFFICULTY GOAL: {diff_info['focus']}

AVAILABLE CONCEPTS IN THIS LECTURE:
{json.dumps(concept_list, indent=2)}

LECTURE TRANSCRIPT EXCERPT:
\"\"\"{transcript_excerpt}\"\"\"

{excluded_block}
REQUIREMENTS:
Generate EXACTLY 7 UNIQUE, HIGH-QUALITY QUESTIONS grounded strictly in the lecture principles:
- 4 Multiple Choice Questions (type: "mcq")
- 3 Short Answer Questions (type: "short_answer")

DIFFICULTY SPECIFICATIONS FOR {difficulty.upper()}:
- MCQ Style: {diff_info['mcq_style']}
- Short Answer Style: {diff_info['short_style']}

CRITICAL PEDAGOGICAL & QUALITY RULES:
1. Every question must be distinct and testing deep comprehension.
2. DO NOT USE REPETITIVE, LOW-LEVEL RECALL PHRASING such as:
   - "Which of the following is mentioned in the transcript?"
   - "According to the speaker/lecture..."
   - "What did the lecturer say about..."
   - "Which statement was stated in the video?"
3. Write authentic conceptual and analytical questions:
   - Test understanding of operational mechanisms, structural invariants, and algorithmic definitions.
   - Test application to concrete engineering or practical scenarios.
   - Test comparing and contrasting related concepts or alternatives.
   - Test diagnosing failure modes, edge cases, and misconception traps.
4. For MCQs:
   - Provide exactly 4 plausible options prefixed with "A. ", "B. ", "C. ", "D. ".
   - Exactly ONE option must be clearly correct.
   - Distractors MUST be plausible misconception-based traps (e.g. confusing linear scan with index lookup, forgetting base cases, assuming unneeded memory overhead, reversing causality).
   - correct_answer must be the full correct option string (e.g. "B. It prevents infinite recursion").
   - explanation must clearly explain why that option is correct and why the alternatives reflect misunderstandings.
5. For Short Answer Questions:
   - Must allow students to explain principles and reasoning in their own words.
   - correct_answer must be a comprehensive reference answer explaining the concept thoroughly.
   - explanation must summarize key conceptual points.
   - rubric must contain 2 to 4 criteria summing to 5.0 marks, with:
     - criterion: clear description of what needs to be demonstrated
     - max_points: numeric points (e.g. 2.0, 1.5, 1.5)
6. Assign each question to the most relevant concept_id, concept_title, and source_timestamp from the concepts list.

OUTPUT FORMAT:
Return a JSON object with a single "questions" key containing an array of exactly 7 question objects:
{{
  "questions": [
    {{
      "id": "q1",
      "type": "mcq",
      "difficulty": "{difficulty}",
      "question_text": "...",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "B. ...",
      "explanation": "...",
      "max_points": 5.0,
      "concept_id": 1,
      "concept_title": "...",
      "source_timestamp": 12.0
    }},
    ... (4 MCQs total: q1, q2, q3, q4),
    {{
      "id": "q5",
      "type": "short_answer",
      "difficulty": "{difficulty}",
      "question_text": "...",
      "options": null,
      "correct_answer": "...",
      "explanation": "...",
      "max_points": 5.0,
      "rubric": [
        {{"criterion": "...", "max_points": 2.0}},
        {{"criterion": "...", "max_points": 1.5}},
        {{"criterion": "...", "max_points": 1.5}}
      ],
      "concept_id": 1,
      "concept_title": "...",
      "source_timestamp": 12.0
    }},
    ... (3 Short Answers total: q5, q6, q7)
  ]
}}
"""

        # Call LLM
        questions = await self._call_llm_for_questions(prompt)

        # Validate and normalize
        normalized = self._normalize_and_validate_questions(
            raw_questions=questions,
            difficulty=difficulty,
            concepts=concepts,
            lecture=lecture,
            seed_offset=seed_offset
        )

        return normalized

    async def _call_llm_for_questions(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Dispatches request to Groq or OpenAI with fast, optimized model prioritization.
        Uses openai/gpt-oss-20b first on Groq (fastest, high throughput, sub-3s response)
        with json_object response_format and max_tokens=3500.
        """
        if self.groq_api_key and self.groq_api_key.strip():
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.groq_api_key.strip()}",
                "Content-Type": "application/json"
            }
            # Prioritize fast 20b model first; 120b and qwen as secondary fallbacks
            models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
        else:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key.strip()}",
                "Content-Type": "application/json"
            }
            models = ["gpt-4o-mini"]

        async with httpx.AsyncClient(timeout=35.0) as client:
            for model_name in models:
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": "You are a specialized university computer science assessment generator. Output strictly valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.35,
                    "max_tokens": 3500
                }

                for attempt in range(2):
                    try:
                        resp = await client.post(url, headers=headers, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            content = data["choices"][0]["message"]["content"].strip()
                            # Clean potential markdown fences
                            content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.MULTILINE)
                            content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE).strip()
                            if not (content.startswith('{') or content.startswith('[')):
                                m = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', content)
                                if m:
                                    content = m.group(1)
                            parsed = json.loads(content)
                            if isinstance(parsed, dict) and "questions" in parsed:
                                return parsed["questions"]
                            elif isinstance(parsed, list) and len(parsed) >= 5:
                                return parsed
                        elif resp.status_code == 429:
                            if attempt == 0:
                                await asyncio.sleep(0.6)
                            else:
                                break
                        elif resp.status_code == 400 and "response_format" in resp.text:
                            payload.pop("response_format", None)
                            continue
                        else:
                            print(f"[AssessmentGen] Model {model_name} returned {resp.status_code}: {resp.text[:180]}")
                            break
                    except Exception as e:
                        print(f"[AssessmentGen] Request error with {model_name} (attempt {attempt+1}): {e}")
                        if attempt == 0:
                            await asyncio.sleep(0.5)

        # Fallback if AI call failed
        return []

    def _normalize_and_validate_questions(
        self,
        raw_questions: List[Dict[str, Any]],
        difficulty: str,
        concepts: List[Concept],
        lecture: Lecture,
        seed_offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Ensures exactly 4 MCQs and 3 Short Answer questions are present,
        properly formatted, numbered q1..q7, with valid options, rubrics, and concept mappings.
        """
        mcqs: List[Dict[str, Any]] = []
        shorts: List[Dict[str, Any]] = []

        fallback_concept_id = concepts[0].id if concepts else 1
        fallback_concept_title = concepts[0].title if concepts else lecture.title
        fallback_ts = float(concepts[0].start_time or 0.0) if concepts else 0.0

        for q in raw_questions:
            q_type = str(q.get("type", "")).lower()
            if "mcq" in q_type or "multiple" in q_type or (q.get("options") and len(q.get("options", [])) >= 2):
                q["type"] = "mcq"
                mcqs.append(q)
            else:
                q["type"] = "short_answer"
                shorts.append(q)

        # If LLM didn't return enough MCQs, synthesize grounded MCQs from concepts
        # Use a different concept for each slot and vary question stems per slot index
        _EASY_MCQ_STEMS = [
            ("What is the primary architectural purpose of '{ct}'?",
             "A. To provide the foundational mechanism for {ctl}.",
             "B. To completely replace all auxiliary subroutines without verification.",
             "C. To prevent data from ever being processed sequentially.",
             "D. To trigger an automatic termination signal regardless of state.",
             "{ct} establishes the core structural foundation for {ctl}."),
            ("Which statement accurately defines the function of '{ct}'?",
             "A. It is the core building block that enables structured understanding of {ctl}.",
             "B. It is an optional extension that is rarely used in practice.",
             "C. It reverses normal data flow to produce unexpected outputs.",
             "D. It eliminates the need for all supporting concepts in this topic.",
             "{ct} serves as a foundational building block for {ctl}."),
            ("What core invariant or rule does '{ct}' enforce?",
             "A. The fundamental boundary conditions and rules governing {ctl}.",
             "B. A secondary helper with no direct influence on core behaviour.",
             "C. An inverse mapping that discards all previously computed state.",
             "D. A temporary placeholder replaced before execution begins.",
             "{ct} governs essential operational boundaries and correctness rules."),
            ("Which of the following best characterizes a key property of '{ct}'?",
             "A. It enforces consistent structure and predictable behaviour in {ctl}.",
             "B. It introduces random variation to avoid deterministic outcomes.",
             "C. It operates only under exceptional error conditions.",
             "D. It is used exclusively for output formatting, not processing.",
             "{ct} guarantees structural consistency and predictable behaviour."),
        ]
        _MOD_MCQ_STEMS = [
            ("How does the concept of '{ct}' interact with other components in this topic?",
             "B. It coordinates the core operational state and guarantees valid transitions.",
             "A. It operates completely independently with zero shared references.",
             "C. It inverts standard evaluation order to bypass validation steps.",
             "D. It converts all dynamic structures into fixed constant literals.",
             "In this lecture, {ct} manages state transitions and ensures proper structural coordination."),
            ("Why is understanding '{ct}' important when working with related concepts?",
             "B. It governs how related components exchange state and avoid inconsistency.",
             "A. It prevents any interaction between independent subsystems.",
             "C. It simplifies all logic by reducing every operation to a single step.",
             "D. It is only relevant during the initialisation phase and ignored afterwards.",
             "{ct} governs the interaction and state exchange between related components."),
            ("What distinguishes '{ct}' from simpler alternatives in this topic?",
             "B. It handles edge cases systematically rather than relying on ad-hoc patches.",
             "A. It is identical to simpler alternatives but uses a different name.",
             "C. It avoids all branching by converting conditions into arithmetic.",
             "D. It delegates all decisions to external configuration without local logic.",
             "{ct} distinguishes itself by handling edge cases systematically."),
            ("When would you apply '{ct}' instead of a naive approach?",
             "B. When correctness under varying conditions must be guaranteed by design.",
             "A. Only when performance is irrelevant and correctness is not required.",
             "C. When the system needs to discard all prior computation and restart.",
             "D. When the problem is too simple to warrant any structured solution.",
             "{ct} is applied when correctness under varying conditions must be guaranteed by design."),
        ]
        _HARD_MCQ_STEMS = [
            ("In a high-throughput production scenario involving '{ct}', which design trade-off is critical?",
             "C. Balancing memory locality against algorithmic complexity to prevent bottlenecks.",
             "A. Maximizing arbitrary recursion depth without termination conditions.",
             "B. Completely eliminating all caching and data structures.",
             "D. Enforcing strict single-threaded execution across all independent nodes.",
             "Under advanced workloads, {ct} requires balancing locality and computational complexity."),
            ("A system built on '{ct}' degrades under peak load. Which root cause is most likely?",
             "C. Contention over shared mutable state introduced by concurrent access to {ctl}.",
             "A. The system is using too few independent subsystems.",
             "B. Logging overhead prevents the CPU from reaching full utilisation.",
             "D. The language runtime disables {ctl} under high concurrency automatically.",
             "Concurrent access to shared mutable state in {ct} is a classic degradation root cause."),
            ("Which failure mode is hardest to detect in a system that misuses '{ct}'?",
             "C. Silent data corruption caused by incorrect boundary assumptions about {ctl}.",
             "A. Immediate crash with a clear stack trace on the first request.",
             "B. Compilation error that prevents deployment.",
             "D. Excessive memory usage that is immediately visible in monitoring dashboards.",
             "Incorrect boundary assumptions in {ct} can cause silent data corruption that evades standard monitoring."),
            ("How should you evolve a '{ct}'-based design when requirements scale 10×?",
             "C. Partition the problem domain and apply {ctl} independently per partition.",
             "A. Remove {ctl} and replace it with a single global lock for simplicity.",
             "B. Increase hardware capacity without changing the design.",
             "D. Convert all {ctl} operations to synchronous single-threaded calls.",
             "Partitioning the domain and applying {ct} independently per partition is the scalable evolution strategy."),
        ]

        while len(mcqs) < 4:
            slot = len(mcqs)   # 0..3
            n_concepts = len(concepts)
            c_idx = (slot + seed_offset) % n_concepts if n_concepts > 0 else 0
            c = concepts[c_idx] if concepts else None
            c_title = c.title if c else lecture.title
            c_id = c.id if c else fallback_concept_id
            c_ts = float(c.start_time or 0.0) if c else fallback_ts
            ctl = c_title.lower()

            if difficulty == "easy":
                stems = _EASY_MCQ_STEMS
            elif difficulty == "moderate":
                stems = _MOD_MCQ_STEMS
            else:
                stems = _HARD_MCQ_STEMS

            tpl = stems[(slot + seed_offset * 2) % len(stems)]
            q_text = tpl[0].format(ct=c_title, ctl=ctl)
            # Determine which option is "correct" (position varies per template)
            # For easy/hard templates: idx 1 is correct (A or C)
            # For moderate templates: idx 1 is correct (B)
            correct = tpl[1].format(ct=c_title, ctl=ctl)
            o_a = tpl[1].format(ct=c_title, ctl=ctl) if tpl[1].startswith("A") else tpl[2].format(ct=c_title, ctl=ctl)
            o_b = tpl[1].format(ct=c_title, ctl=ctl) if tpl[1].startswith("B") else tpl[2].format(ct=c_title, ctl=ctl) if tpl[2].startswith("B") else tpl[3].format(ct=c_title, ctl=ctl)
            o_c = tpl[1].format(ct=c_title, ctl=ctl) if tpl[1].startswith("C") else tpl[3].format(ct=c_title, ctl=ctl) if tpl[3].startswith("C") else tpl[4].format(ct=c_title, ctl=ctl)
            o_d = tpl[4].format(ct=c_title, ctl=ctl) if tpl[4].startswith("D") else tpl[5].format(ct=c_title, ctl=ctl) if len(tpl) > 5 and tpl[5].startswith("D") else f"D. None of the above options apply to {c_title}."
            opts = [o_a, o_b, o_c, o_d]
            expl = tpl[-1].format(ct=c_title, ctl=ctl)

            mcqs.append({
                "type": "mcq",
                "question_text": q_text,
                "options": opts,
                "correct_answer": correct,
                "explanation": expl,
                "max_points": 5.0,
                "concept_id": c_id,
                "concept_title": c_title,
                "source_timestamp": c_ts
            })

        # If LLM didn't return enough Short Answers, synthesize grounded items
        # Use different concept slots and varied question stems
        _EASY_SA_STEMS = [
            ("Define '{ct}' in your own words and explain its primary architectural purpose.",
             "{ct} is the core principle used to manage and understand the lecture topic. Its primary purpose is to ensure clear structure and predictable execution.",
             "Accurate definition of {ct}", "Clear explanation of primary purpose"),
            ("Describe a practical scenario or analogy illustrating how '{ct}' operates.",
             "A practical scenario for {ct} is where a structured, indexed organization leads to predictable, repeatable outcomes without exhaustive searching.",
             "Appropriate real-world analogy or example", "Connection of example to {ct}"),
            ("What fundamental problem does '{ct}' address, and what unintended consequences occur if it is omitted?",
             "{ct} solves the problem of unpredictability and linear performance bottlenecks by providing structured state organization.",
             "Clear identification of the problem {ct} addresses", "Effective explanation of consequences if omitted"),
        ]
        _MOD_SA_STEMS = [
            ("Explain the mechanism of '{ct}'. Why is this approach favored over simpler alternatives?",
             "{ct} works by structuring state and applying systematic rules. It is favored because it avoids common edge cases and ensures consistency.",
             "Explanation of operational mechanism of {ct}", "Comparison or justification against alternative approaches"),
            ("How does '{ct}' differ from related concepts in this lecture? What makes it uniquely suited to its role?",
             "{ct} differs from related concepts by providing tighter guarantees on correctness and structure. Its systematic approach makes it uniquely suited when reliability matters more than simplicity.",
             "Clear comparison between {ct} and related concepts", "Explanation of what makes {ct} uniquely suited"),
            ("Walk through a step-by-step scenario where applying '{ct}' correctly leads to a successful outcome. What could go wrong if it were misapplied?",
             "Applying {ct} correctly involves following its structured steps: first identify inputs, then process them systematically, and validate outputs. Misapplying it — such as skipping validation — leads to inconsistent or incorrect results.",
             "Step-by-step correct application scenario for {ct}", "Identification of consequences of misapplication"),
        ]
        _HARD_SA_STEMS = [
            ("Consider a system utilizing '{ct}'. How would you handle edge cases and optimize performance under heavy load?",
             "To handle edge cases in {ct}, validate boundary conditions early. For performance optimization, minimize unnecessary recomputations and utilize efficient data layouts.",
             "Identification and handling of boundary edge cases", "Realistic performance optimization strategies"),
            ("You are designing a large-scale system where '{ct}' is a central component. The system must handle 10× more load than initially planned. What architectural changes would you make and why?",
             "To scale {ct} 10×, partition the problem domain so each partition applies {ct} independently. Use caching, reduce synchronization overhead, and monitor boundary conditions proactively to prevent cascading failures.",
             "Architectural changes appropriate for 10× scale involving {ct}", "Justification linking changes to {ct}'s properties"),
            ("A team debugging a production system discovers that '{ct}' is producing incorrect outputs only under specific conditions. Walk through your debugging process and explain what root causes you would investigate first.",
             "I would first isolate the conditions under which {ct} fails by reproducing with minimal inputs. Then I would inspect boundary conditions, shared state mutations, and ordering assumptions — common sources of subtle failure in {ct}-based designs.",
             "Systematic debugging approach for {ct} failures", "Identification of plausible root causes specific to {ct}"),
        ]

        while len(shorts) < 3:
            slot = len(shorts)   # 0..2
            n_concepts = len(concepts)
            # Offset by 1 from MCQ slots so we don't repeat the same concept
            c_idx = (slot + 1 + seed_offset) % n_concepts if n_concepts > 0 else 0
            c = concepts[c_idx] if concepts else None
            c_title = c.title if c else lecture.title
            c_id = c.id if c else fallback_concept_id
            c_ts = float(c.start_time or 0.0) if c else fallback_ts
            ctl = c_title.lower()

            if difficulty == "easy":
                stems = _EASY_SA_STEMS
            elif difficulty == "moderate":
                stems = _MOD_SA_STEMS
            else:
                stems = _HARD_SA_STEMS

            tpl = stems[(slot + seed_offset * 2) % len(stems)]
            q_text = tpl[0].format(ct=c_title, ctl=ctl)
            ref_ans = tpl[1].format(ct=c_title, ctl=ctl)
            rubric = [
                {"criterion": tpl[2].format(ct=c_title, ctl=ctl), "max_points": 2.5},
                {"criterion": tpl[3].format(ct=c_title, ctl=ctl), "max_points": 2.5}
            ]

            shorts.append({
                "type": "short_answer",
                "question_text": q_text,
                "options": None,
                "correct_answer": ref_ans,
                "explanation": f"Key concept: {c_title}",
                "max_points": 5.0,
                "rubric": rubric,
                "concept_id": c_id,
                "concept_title": c_title,
                "source_timestamp": c_ts
            })

        # Trim to exactly 4 MCQs and 3 Short Answers
        final_mcqs = mcqs[:4]
        final_shorts = shorts[:3]

        result: List[Dict[str, Any]] = []

        # Format MCQs (q1..q4)
        for idx, m in enumerate(final_mcqs, start=1):
            opts = m.get("options") or []
            if len(opts) < 4:
                # Ensure 4 options
                opts = [
                    opts[0] if len(opts) > 0 else "A. Option A",
                    opts[1] if len(opts) > 1 else "B. Option B",
                    opts[2] if len(opts) > 2 else "C. Option C",
                    opts[3] if len(opts) > 3 else "D. Option D"
                ]

            corr = str(m.get("correct_answer") or opts[0]).strip()

            result.append({
                "id": f"q{idx}",
                "type": "mcq",
                "difficulty": difficulty,
                "question_text": str(m.get("question_text", f"Question {idx}")).strip(),
                "options": [str(o).strip() for o in opts[:4]],
                "correct_answer": corr,
                "explanation": str(m.get("explanation") or "Refer to the lecture explanation.").strip(),
                "max_points": 5.0,
                "concept_id": m.get("concept_id") or fallback_concept_id,
                "concept_title": m.get("concept_title") or fallback_concept_title,
                "source_timestamp": float(m.get("source_timestamp") or fallback_ts)
            })

        # Format Short Answers (q5..q7)
        for idx, s in enumerate(final_shorts, start=5):
            rubric = s.get("rubric")
            if not rubric or not isinstance(rubric, list) or len(rubric) == 0:
                rubric = [
                    {"criterion": "Accurate explanation of the core concept", "max_points": 2.5},
                    {"criterion": "Clear reasoning and supporting details", "max_points": 2.5}
                ]

            result.append({
                "id": f"q{idx}",
                "type": "short_answer",
                "difficulty": difficulty,
                "question_text": str(s.get("question_text", f"Question {idx}")).strip(),
                "options": None,
                "correct_answer": str(s.get("correct_answer", "")).strip(),
                "explanation": str(s.get("explanation") or "Conceptual breakdown from the lecture.").strip(),
                "max_points": 5.0,
                "rubric": rubric,
                "concept_id": s.get("concept_id") or fallback_concept_id,
                "concept_title": s.get("concept_title") or fallback_concept_title,
                "source_timestamp": float(s.get("source_timestamp") or fallback_ts)
            })

        return result


assessment_generation_service = AssessmentGenerationService()
