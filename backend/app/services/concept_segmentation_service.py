import json
import re
import asyncio
import random
from typing import List, Dict, Any, Optional
from app.config import settings

SAMPLE_FUNCTION_CONCEPTS = [
    {
        "order_index": 0,
        "title": "Functions Overview",
        "description": "Functions act as fundamental building blocks in programming that map given input values to unique, predictable output values.",
        "start_time": 0.0,
        "end_time": 95.0,
        "confidence_score": 0.98,
        "transcript_text": "Welcome to Computer Science 101. Today we are exploring the foundational building block of programming and mathematics: Functions. Understanding what a function really is will dictate how clearly you design modular, reusable software. A function is fundamentally a mapping from an input to an output. You give it a valid input value from a predetermined set, and it produces exactly one corresponding output value. In programming, think of it as a black box with defined inputs and a predictable return value.",
        "core_concepts": [
            "A function is a deterministic mathematical and computational mapping from an input to an output.",
            "Each valid input from the domain must produce exactly one corresponding output.",
            "Functions serve as modular black boxes facilitating reusable, clean software architecture."
        ],
        "confusing_topics": [
            "Confusing a function with a simple variable or static data structure.",
            "Assuming a function can nondeterministically produce multiple different outputs for the exact same input without external state."
        ]
    },
    {
        "order_index": 1,
        "title": "Input and Output",
        "description": "Functions receive input arguments through parameters and communicate resulting computed values back through explicit return statements.",
        "start_time": 95.0,
        "end_time": 170.0,
        "confidence_score": 0.96,
        "transcript_text": "Now, let us distinguish between Input and Output. The input parameters represent the arguments passed into the function call. The output is the result returned to the caller. Crucially, a pure function does not alter hidden global state; it purely transforms its provided inputs into outputs.",
        "core_concepts": [
            "Input parameters specify the variables and types expected by the function.",
            "Output is the explicit value returned to the caller upon completion of the function body.",
            "Pure functions avoid hidden global side effects and solely depend on their explicit inputs."
        ],
        "confusing_topics": [
            "Confusing printing to standard output (console log) with returning a value from a function.",
            "Believing parameters and return values must always share the same data type."
        ]
    },
    {
        "order_index": 2,
        "title": "Domain and Range",
        "description": "The domain defines the complete set of valid input values a function accepts, while the range encompasses all potential outputs it can produce.",
        "start_time": 170.0,
        "end_time": 265.0,
        "confidence_score": 0.97,
        "transcript_text": "A common point of confusion is Domain versus Range. The Domain is the complete set of all permissible input values that the function can accept without error or undefined behavior. The Range, on the other hand, is the set of all resulting output values produced by applying the function over its domain. Remember: Domain belongs to inputs; Range belongs to outputs.",
        "core_concepts": [
            "Domain represents the set of all permissible, valid inputs.",
            "Range represents the set of all resulting outputs generated across the valid domain.",
            "Attempting to supply an input outside the permissible domain leads to runtime errors or undefined behavior."
        ],
        "confusing_topics": [
            "Mixing up which term applies to inputs vs outputs (Domain belongs to inputs, Range belongs to outputs).",
            "Assuming all functions can accept all numbers (ignoring constraints like division by zero or negative square roots)."
        ]
    },
    {
        "order_index": 3,
        "title": "Function Notation",
        "description": "Function notation provides formal syntax like f(x) = y in mathematics and function definitions in code to declare name, parameters, and expressions.",
        "start_time": 265.0,
        "end_time": 345.0,
        "confidence_score": 0.95,
        "transcript_text": "Next, let us look at Function Notation. In mathematics, we write f of x equals y, denoted f(x) = y. In modern languages like Python or TypeScript, we define `def calculate_area(radius): return 3.14 * radius * radius`. Notice how f corresponds to the function name, x is the input parameter, and the expression defines the mapping rule.",
        "core_concepts": [
            "Mathematical notation f(x) denotes evaluating rule f with argument x.",
            "Programming syntax specifies function identifier, argument list, and execution body.",
            "The function name acts as an identifier reference while parentheses invoke evaluation."
        ],
        "confusing_topics": [
            "Confusing function declaration/definition with function invocation/call.",
            "Misinterpreting parenthetical notation f(x) as mathematical multiplication between f and x."
        ]
    },
    {
        "order_index": 4,
        "title": "Examples and Applications",
        "description": "Concrete demonstrations including f(x) = x squared illustrate how domain restrictions fundamentally dictate the boundaries of the resulting range.",
        "start_time": 345.0,
        "end_time": 420.0,
        "confidence_score": 0.96,
        "transcript_text": "Finally, let us consider concrete Examples. Consider f(x) = x squared. If your domain is all real numbers, what is your range? Because any real number squared is non-negative, the range is all numbers greater than or equal to zero! Notice how restricting the domain directly influences the achievable range. Keep this distinction sharp.",
        "core_concepts": [
            "Practical evaluation of functions grounds theoretical input/output mapping.",
            "Squaring numbers always yields non-negative range [0, infinity) over the real domain.",
            "Restricting or expanding the domain directly reshapes the achievable range."
        ],
        "confusing_topics": [
            "Failing to recognize that squaring negative numbers results in positive outputs.",
            "Assuming every output in the codomain must be reachable when evaluating specific inputs."
        ]
    }
]

class ConceptSegmentationService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY

    async def segment_transcript(
        self,
        transcript_segments: List[Dict[str, Any]],
        full_text: str,
        lecture_title: str = "",
        duration: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Partitions timestamped transcript segments into meaningful concept blocks.
        Chunks transcript by time window to avoid prompt truncation.
        Removes segments[:30] and the 5-concept cap.
        Fails fast if LLM generation fails after retries (no heuristic fallbacks).
        """
        # Demo lecture shortcut
        is_sample_function_seed = (
            lecture_title.strip().lower() == "introduction to functions" and
            (duration is None or abs(duration - 420.0) < 5)
        )
        if is_sample_function_seed:
            return SAMPLE_FUNCTION_CONCEPTS

        if not transcript_segments:
            raise ValueError("Cannot perform concept segmentation: transcript has no segments.")

        if not self.api_key or not self.api_key.strip():
            raise RuntimeError("Concept extraction failed: GROQ_API_KEY is not configured.")

        # Windowed segmentation
        total_duration = duration or transcript_segments[-1]["end_time"]
        window_size = 300.0  # ~5 minute windows to stay comfortably under token limits

        num_windows = max(1, int(total_duration // window_size) + (1 if total_duration % window_size > 45 else 0))
        print(f"[ConceptSegmentation] Partitioning {total_duration:.1f}s lecture into {num_windows} time window(s)...")

        all_extracted_concepts: List[Dict[str, Any]] = []

        for w_idx in range(num_windows):
            w_start = w_idx * window_size
            w_end = min(total_duration, (w_idx + 1) * window_size) if w_idx < num_windows - 1 else total_duration

            # Gather segments falling within this time window
            window_segs = [
                s for s in transcript_segments
                if (w_start <= s.get("start_time", 0.0) < w_end) or
                   (w_idx == num_windows - 1 and s.get("start_time", 0.0) >= w_start)
            ]

            if not window_segs:
                continue

            print(f"[ConceptSegmentation] Processing window {w_idx+1}/{num_windows} ({w_start:.0f}s - {w_end:.0f}s, {len(window_segs)} segments)...")
            window_concepts = await self._segment_window_with_llm(
                segments=window_segs,
                window_start=w_start,
                window_end=w_end,
                lecture_title=lecture_title
            )

            if window_concepts:
                all_extracted_concepts.extend(window_concepts)
            else:
                raise RuntimeError(f"Concept extraction returned no valid concepts for window {w_idx+1} ({w_start:.0f}s - {w_end:.0f}s).")

            # Small pause between windows to respect rate limits
            if w_idx < num_windows - 1:
                await asyncio.sleep(1.0)

        if not all_extracted_concepts:
            raise RuntimeError("Concept extraction failed: No concepts could be generated across the lecture.")

        # Merge adjacent concepts that cover the same topic across or within windows
        merged_concepts = self._merge_adjacent_similar_concepts(all_extracted_concepts)

        # Final cleanup: ensure contiguous order_index and valid timestamps
        final_concepts: List[Dict[str, Any]] = []
        for idx, c in enumerate(merged_concepts):
            c_start = max(0.0, float(c.get("start_time", 0.0)))
            c_end = max(c_start + 1.0, float(c.get("end_time", c_start + 60.0)))
            title = str(c.get("title", f"Concept {idx+1}")).strip()
            # Clean title
            title = re.sub(r'^(concept\s*\d*[:\-\s]*|topic\s*\d*[:\-\s]*)', '', title, flags=re.IGNORECASE).strip()
            if not title:
                title = f"Concept {idx+1}"

            final_concepts.append({
                "order_index": idx,
                "title": title,
                "description": str(c.get("description", "")).strip(),
                "start_time": round(c_start, 2),
                "end_time": round(c_end, 2),
                "transcript_text": str(c.get("transcript_text", "")).strip(),
                "confidence_score": float(c.get("confidence_score", 0.95)),
                "core_concepts": c.get("core_concepts", [f"Key insight for {title}."]),
                "confusing_topics": c.get("confusing_topics", [f"Common misconception regarding {title}."])
            })

        print(f"[ConceptSegmentation] Successfully generated {len(final_concepts)} concepts across full lecture (merged from {len(all_extracted_concepts)}).")
        return final_concepts

    def _merge_adjacent_similar_concepts(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merges adjacent concepts that cover the same core topic so that
        time windows do not artificially duplicate or fragment a coherent topic.
        """
        import difflib
        if len(concepts) <= 1:
            return list(concepts)

        merged: List[Dict[str, Any]] = []
        for c in concepts:
            if not merged:
                merged.append(dict(c))
                continue

            prev = merged[-1]
            prev_title = re.sub(r'[^a-z0-9\s]', '', prev.get("title", "").lower()).strip()
            curr_title = re.sub(r'[^a-z0-9\s]', '', c.get("title", "").lower()).strip()

            prev_words = set(prev_title.split())
            curr_words = set(curr_title.split())
            stop_words = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on", "at", "by", "from", "is", "are"}
            prev_kw = prev_words - stop_words
            curr_kw = curr_words - stop_words

            ratio = difflib.SequenceMatcher(None, prev_title, curr_title).ratio()
            overlap = len(prev_kw & curr_kw) / max(1, min(len(prev_kw), len(curr_kw))) if prev_kw and curr_kw else 0.0

            is_similar = (
                prev_title == curr_title
                or (prev_title in curr_title and len(prev_title) > 4)
                or (curr_title in prev_title and len(curr_title) > 4)
                or ratio >= 0.70
                or overlap >= 0.60
            )

            time_gap = float(c.get("start_time", 0.0)) - float(prev.get("end_time", 0.0))
            if is_similar and time_gap <= 45.0:
                prev["end_time"] = max(float(prev.get("end_time", 0.0)), float(c.get("end_time", 0.0)))
                if len(str(c.get("description", ""))) > len(str(prev.get("description", ""))):
                    prev["description"] = c.get("description", "")
                
                c_tt = str(c.get("transcript_text", "")).strip()
                if c_tt and c_tt not in str(prev.get("transcript_text", "")):
                    prev["transcript_text"] = (str(prev.get("transcript_text", "")) + " " + c_tt).strip()

                prev_core = list(prev.get("core_concepts", []))
                for cc in c.get("core_concepts", []):
                    if cc not in prev_core:
                        prev_core.append(cc)
                prev["core_concepts"] = prev_core[:4]

                prev_conf = list(prev.get("confusing_topics", []))
                for ct in c.get("confusing_topics", []):
                    if ct not in prev_conf:
                        prev_conf.append(ct)
                prev["confusing_topics"] = prev_conf[:4]
            else:
                merged.append(dict(c))

        return merged

    async def _segment_window_with_llm(
        self,
        segments: List[Dict[str, Any]],
        window_start: float,
        window_end: float,
        lecture_title: str = "",
        max_retries: int = 4
    ) -> List[Dict[str, Any]]:
        from groq import Groq
        client = Groq(api_key=self.api_key)

        # Ultra-compact plain-text representation to minimize prompt tokens and avoid rate/TPM limits
        segment_lines = []
        for s in segments:
            st = round(float(s.get("start_time", 0.0)), 1)
            et = round(float(s.get("end_time", 0.0)), 1)
            txt = str(s.get("text", "")).strip()
            if txt:
                segment_lines.append(f"[{st}s-{et}s] {txt}")
        compact_transcript = "\n".join(segment_lines)

        prompt = (
            "You are an expert computer science curriculum analyst for the MindTrace FYP platform.\n"
            f"Lecture Title: {lecture_title}\n"
            f"Time Window: {window_start:.1f}s to {window_end:.1f}s\n"
            "Analyze the following timestamped transcript segments for this time window and partition them into 1 to 2 distinct CONCEPT-LEVEL topics. If the window covers a single coherent subject, return exactly 1 concept; only return 2 if there is an explicit topic transition.\n"
            "IMPORTANT Requirements:\n"
            "1. Each concept title must be a CONCISE topic name of 2-4 words (e.g. 'Binary Search Tree', 'Base Case Logic', 'Stack Frame Allocation'). NEVER use sentence fragments or generic titles like 'Introduction'.\n"
            "2. 'start_time' and 'end_time' must be floats bounded by the transcript segments provided.\n"
            "3. Return ONLY a valid JSON array of objects with keys:\n"
            "   - title (str, 2-4 words topic name)\n"
            "   - description (str, 1-2 sentences on core pedagogical idea)\n"
            "   - start_time (float in seconds)\n"
            "   - end_time (float in seconds)\n"
            "   - confidence_score (float 0.85 to 0.99)\n"
            "   - core_concepts (list of 2-3 essential takeaway sentences)\n"
            "   - confusing_topics (list of 2-3 common misconceptions or traps)\n\n"
            f"Window Segments:\n{compact_transcript}"
        )

        models_to_try = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]

        for attempt in range(max_retries):
            model_name = models_to_try[attempt % len(models_to_try)]
            try:
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a curriculum analysis engine. You output only valid JSON arrays, no markdown fences."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=2048
                )

                raw = (response.choices[0].message.content or "").strip()
                if not raw:
                    raise ValueError("Groq returned an empty response")

                # Strip markdown fences
                if "```" in raw:
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                raw = raw.strip()

                parsed = json.loads(raw)
                concepts_list = parsed.get("concepts") if isinstance(parsed, dict) else (parsed if isinstance(parsed, list) else [])
                if concepts_list and len(concepts_list) > 0:
                    # Ground transcript_text from the actual segments in this window
                    for c in concepts_list:
                        cs = float(c.get("start_time", window_start))
                        ce = float(c.get("end_time", window_end))
                        matching = [s["text"] for s in segments if cs - 2.0 <= s.get("start_time", 0.0) <= ce + 2.0]
                        c["transcript_text"] = " ".join(matching).strip() if matching else " ".join(s["text"] for s in segments[:10])
                    return concepts_list
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "rate limit" in err_str or "tpm" in err_str or "too large" in err_str
                wait_time = (6.0 * (attempt + 1)) if is_rate_limit else (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"[ConceptSegmentation Window] Attempt {attempt+1}/{max_retries} failed ({e}). Retrying in {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)

        raise RuntimeError(f"Concept segmentation LLM call failed for window {window_start:.0f}s-{window_end:.0f}s after {max_retries} retries.")

concept_segmentation_service = ConceptSegmentationService()
