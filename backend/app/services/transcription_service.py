import os
import re
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from app.config import settings

SAMPLE_FUNCTION_TRANSCRIPT = [
    {
        "start_time": 0.0,
        "end_time": 38.0,
        "speaker": "Prof. Alan",
        "text": "Welcome to Computer Science 101. Today we are exploring the foundational building block of programming and mathematics: Functions. Understanding what a function really is will dictate how clearly you design modular, reusable software."
    },
    {
        "start_time": 38.0,
        "end_time": 95.0,
        "speaker": "Prof. Alan",
        "text": "A function is fundamentally a mapping from an input to an output. You give it a valid input value from a predetermined set, and it produces exactly one corresponding output value. In programming, think of it as a black box with defined inputs and a predictable return value."
    },
    {
        "start_time": 95.0,
        "end_time": 170.0,
        "speaker": "Prof. Alan",
        "text": "Now, let us distinguish between Input and Output. The input parameters represent the arguments passed into the function call. The output is the result returned to the caller. Crucially, a pure function does not alter hidden global state; it purely transforms its provided inputs into outputs."
    },
    {
        "start_time": 170.0,
        "end_time": 265.0,
        "speaker": "Prof. Alan",
        "text": "A common point of confusion is Domain versus Range. The Domain is the complete set of all permissible input values that the function can accept without error or undefined behavior. The Range, on the other hand, is the set of all resulting output values produced by applying the function over its domain. Remember: Domain belongs to inputs; Range belongs to outputs."
    },
    {
        "start_time": 265.0,
        "end_time": 345.0,
        "speaker": "Prof. Alan",
        "text": "Next, let us look at Function Notation. In mathematics, we write f of x equals y, denoted f(x) = y. In modern languages like Python or TypeScript, we define `def calculate_area(radius): return 3.14 * radius * radius`. Notice how f corresponds to the function name, x is the input parameter, and the expression defines the mapping rule."
    },
    {
        "start_time": 345.0,
        "end_time": 420.0,
        "speaker": "Prof. Alan",
        "text": "Finally, let us consider concrete Examples. Consider f(x) = x squared. If your domain is all real numbers, what is your range? Because any real number squared is non-negative, the range is all numbers greater than or equal to zero! Notice how restricting the domain directly influences the achievable range. Keep this distinction sharp."
    }
]

# Domain-specific prompt hint to ground Whisper's vocabulary and suppress hallucinations
COMPUTER_SCIENCE_PROMPT = (
    "Computer science university lecture about programming concepts, recursion, "
    "base cases, recursive calls, functions, parameters, return values, call stack, algorithms."
)

class TranscriptionService:
    def __init__(self):
        self._whisper_model = None
        self._loaded_model_size = None
        self._model_size = os.getenv("WHISPER_MODEL_SIZE", "base")

    def get_whisper_model(self, model_size: Optional[str] = None):
        """
        Loads and caches the local faster-whisper model on CPU using INT8 quantization.
        Runs offline without external API costs.
        """
        target_size = model_size or self._model_size
        if self._whisper_model is None or self._loaded_model_size != target_size:
            from faster_whisper import WhisperModel
            print(f"[LocalSTT] Initializing local Faster-Whisper '{target_size}' model on CPU (int8)...")
            self._whisper_model = WhisperModel(target_size, device="cpu", compute_type="int8")
            self._loaded_model_size = target_size
            print(f"[LocalSTT] Local model '{target_size}' loaded and ready for transcription.")
        return self._whisper_model

    def check_transcript_quality(self, full_text: str, segments: List[Dict[str, Any]]) -> Optional[str]:
        """
        Basic sanity check after transcription:
        1. Checks for Cyrillic / non-Latin characters (hallucination sign in silence/noise).
        2. Checks for extremely short transcripts (< 10 words).
        Returns a human-readable warning message if quality is suspicious, else None.
        """
        if not full_text:
            return "Transcript quality is low: no audible speech detected in the recording."

        # Detect Cyrillic characters (Russian, Bulgarian, etc. often hallucinated by Whisper on noise)
        cyrillic_chars = re.findall(r'[\u0400-\u04FF]', full_text)
        if len(cyrillic_chars) >= 2:
            return "Transcript quality is low: unexpected foreign characters detected (potential silence hallucination)."

        # Check for extremely short transcripts (< 10 words)
        if len(full_text.split()) < 10:
            return "Transcript quality is low: very short audio or minimal audible speech detected."

        # Check for repetitive loops (Whisper getting stuck on a single hallucinated phrase)
        words = full_text.lower().split()
        if len(words) >= 20:
            first_phrase = " ".join(words[:4])
            phrase_occurrences = full_text.lower().count(first_phrase)
            if phrase_occurrences >= 5:
                return "Transcript quality is low: repetitive phrases detected in audio processing."

        return None

    async def _transcribe_with_groq(
        self,
        file_path: str,
        audio_language: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribes or translates audio via Groq Cloud Whisper API.
        For Urdu / Mixed Urdu-English:
          Uses the /audio/translations endpoint with 'whisper-large-v3' (translates to English).
          Note: 'whisper-large-v3-turbo' DOES NOT support translation on Groq.
        For English:
          Uses the /audio/transcriptions endpoint with 'whisper-large-v3'.
        """
        groq_key = settings.GROQ_API_KEY.strip()
        if not groq_key:
            return None

        if not os.path.exists(file_path):
            return None

        file_size = os.path.getsize(file_path)
        # Groq payload limit is 25MB
        if file_size > 25 * 1024 * 1024:
            print(f"[GroqWhisper] File size {file_size} exceeds 25MB Groq limit; falling back to local model.")
            return None

        is_urdu_or_mixed = audio_language.lower().strip() in ["ur", "urdu", "mixed", "ur-en", "urdu/mixed"]

        if is_urdu_or_mixed:
            # Translation endpoint converts Urdu speech to English text
            url = "https://api.groq.com/openai/v1/audio/translations"
            model_name = "whisper-large-v3"  # Only whisper-large-v3 supports translations on Groq!
        else:
            # Transcription endpoint for pure English lectures
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            model_name = "whisper-large-v3"

        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".m4a": "audio/mp4",
            ".ogg": "audio/ogg",
            ".webm": "audio/webm",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
        }
        mime = mime_map.get(ext, "application/octet-stream")

        headers = {
            "Authorization": f"Bearer {groq_key}",
        }

        try:
            print(f"[GroqWhisper] Sending audio to Groq ({model_name}, mode={'translation' if is_urdu_or_mixed else 'transcription'})...")
            async with httpx.AsyncClient(timeout=180.0) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f, mime)}
                    data: Dict[str, Any] = {
                        "model": model_name,
                        "prompt": COMPUTER_SCIENCE_PROMPT,
                        "temperature": "0",  # Greedy decoding reduces silence hallucinations
                        "response_format": "verbose_json",
                    }
                    if not is_urdu_or_mixed:
                        data["language"] = "en"

                    response = await client.post(url, headers=headers, files=files, data=data)

            if response.status_code != 200:
                print(f"[GroqWhisper] HTTP error {response.status_code}: {response.text}")
                return None

            resp_json = response.json()
            raw_segments = resp_json.get("segments", [])

            segments = []
            for idx, seg in enumerate(raw_segments):
                text = seg.get("text", "").strip()
                if text:
                    segments.append({
                        "start_time": round(float(seg.get("start", 0.0)), 2),
                        "end_time": round(float(seg.get("end", 0.0)), 2),
                        "text": text,
                        "speaker": "Instructor",
                        "segment_index": idx
                    })

            full_text = resp_json.get("text", "").strip()
            if not full_text and segments:
                full_text = " ".join(s["text"] for s in segments)

            duration = float(resp_json.get("duration", segments[-1]["end_time"] if segments else 0.0))

            return {
                "provider": f"Groq Whisper ({model_name} {'Translation' if is_urdu_or_mixed else 'Transcription'})",
                "full_text": full_text,
                "word_count": len(full_text.split()),
                "duration": round(duration, 2),
                "language": "en",
                "segments": segments
            }
        except Exception as e:
            print(f"[GroqWhisper] API request failed: {e}. Falling back to local Faster-Whisper.")
            return None

    def _transcribe_locally_sync(
        self,
        audio_path: str,
        audio_language: str = "en",
        model_size: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs synchronous speech-to-text / translation using local Faster-Whisper on CPU.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Media file not found for transcription: {audio_path}")

        file_size = os.path.getsize(audio_path)
        if file_size < 100:
            raise ValueError("Uploaded audio file is empty or corrupted.")

        is_urdu_or_mixed = audio_language.lower().strip() in ["ur", "urdu", "mixed", "ur-en", "urdu/mixed"]

        task = "translate" if is_urdu_or_mixed else "transcribe"
        language = "ur" if is_urdu_or_mixed else "en"

        try:
            model = self.get_whisper_model(model_size)
            segments_gen, info = model.transcribe(
                audio_path,
                task=task,
                language=language,
                initial_prompt=COMPUTER_SCIENCE_PROMPT,
                temperature=0.0,
                beam_size=3,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            raw_segments = list(segments_gen)
        except Exception as e:
            print(f"[LocalSTT] Transcription with model '{model_size or self._model_size}' failed: {e}. Trying tiny model fallback...")
            try:
                model = self.get_whisper_model("tiny")
                segments_gen, info = model.transcribe(
                    audio_path,
                    task=task,
                    language=language,
                    initial_prompt=COMPUTER_SCIENCE_PROMPT,
                    temperature=0.0,
                    beam_size=1,
                    vad_filter=True
                )
                raw_segments = list(segments_gen)
            except Exception as e2:
                raise ValueError(
                    f"Local speech transcription failed: {str(e2)}. "
                    f"Please ensure the file is a valid audio/video recording (WAV, MP3, MP4, M4A, OGG)."
                )

        segments = []
        for idx, seg in enumerate(raw_segments):
            text = seg.text.strip()
            if text:
                segments.append({
                    "start_time": round(float(seg.start), 2),
                    "end_time": round(float(seg.end), 2),
                    "text": text,
                    "speaker": "Instructor",
                    "segment_index": idx
                })

        full_text = " ".join(s["text"] for s in segments).strip()
        detected_dur = float(info.duration) if hasattr(info, "duration") and info.duration else (segments[-1]["end_time"] if segments else 0.0)

        if not full_text:
            raise ValueError(
                "No intelligible speech could be detected in the uploaded audio/video file. "
                "Please ensure the recording contains audible lecture dialogue, or provide an accompanying transcript."
            )

        provider_label = f"Local Faster-Whisper ({self._loaded_model_size} CPU - {'Translation' if is_urdu_or_mixed else 'Transcription'})"

        return {
            "provider": provider_label,
            "full_text": full_text,
            "word_count": len(full_text.split()),
            "duration": round(detected_dur, 2),
            "language": "en",
            "segments": segments
        }

    async def transcribe_audio(
        self,
        file_path: str,
        filename: str = "",
        title: str = "",
        detected_duration: Optional[float] = None,
        manual_transcript: Optional[str] = None,
        is_demo: bool = False,
        audio_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Transcribe audio recording:
        1. If manual transcript text or subtitle file is provided, parses genuine timestamped utterances.
        2. If demo lecture, uses pre-seeded CS101 Functions transcript.
        3. If Groq API key is present: runs Groq Whisper Translation (whisper-large-v3) or Transcription.
        4. Fallback / offline: Local Faster-Whisper with explicit translation/transcription task and temperature=0.
        5. Performs post-transcription sanity check and attaches quality warning if noise is detected.
        """
        # 1. Manual transcript provided during upload
        if manual_transcript and manual_transcript.strip():
            result = self.parse_manual_transcript(
                manual_transcript.strip(),
                duration=detected_duration or 120.0
            )
            result["quality_warning"] = self.check_transcript_quality(result["full_text"], result["segments"])
            return result

        # 2. Pre-seeded demo lecture
        is_sample_function_seed = (
            is_demo or
            (title.strip().lower() == "introduction to functions" and
             (detected_duration is None or abs(detected_duration - 420.0) < 10))
        )
        if is_sample_function_seed:
            segments = []
            for idx, item in enumerate(SAMPLE_FUNCTION_TRANSCRIPT):
                segments.append({
                    "start_time": item["start_time"],
                    "end_time": item["end_time"],
                    "text": item["text"],
                    "speaker": item["speaker"],
                    "segment_index": idx
                })
            full_text = " ".join(s["text"] for s in segments)
            return {
                "provider": "MindTrace Demo Lecture Transcript",
                "full_text": full_text,
                "word_count": len(full_text.split()),
                "duration": 420.0,
                "segments": segments,
                "quality_warning": None
            }

        # 3. Try Groq Whisper Cloud (fast, high accuracy, whisper-large-v3 translation)
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
            groq_res = await self._transcribe_with_groq(file_path, audio_language=audio_language)
            if groq_res:
                groq_res["quality_warning"] = self.check_transcript_quality(groq_res["full_text"], groq_res["segments"])
                return groq_res

        # 4. Local Faster-Whisper (non-blocking thread on CPU)
        print(f"[TranscriptionService] Processing '{filename or os.path.basename(file_path)}' via Local Faster-Whisper (mode: {audio_language})...")
        local_res = await asyncio.to_thread(self._transcribe_locally_sync, file_path, audio_language)
        local_res["quality_warning"] = self.check_transcript_quality(local_res["full_text"], local_res["segments"])
        return local_res

    def parse_manual_transcript(self, raw_text: str, duration: float) -> Dict[str, Any]:
        """
        Parses manual transcript text, supporting SRT, VTT, or plain text notes.
        """
        target_duration = max(5.0, round(float(duration), 2)) if duration else 120.0

        # Check if SRT format (00:00:01,000 --> 00:00:04,000)
        srt_pattern = re.compile(
            r'(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n(.*?)(?=\n\s*\d+\s*\n|\Z)',
            re.DOTALL
        )
        srt_matches = list(srt_pattern.finditer(raw_text))

        if srt_matches:
            segments = []
            for idx, match in enumerate(srt_matches):
                start_str = match.group(2).replace(',', '.')
                end_str = match.group(3).replace(',', '.')
                text = " ".join(match.group(4).strip().split())

                def parse_time(ts_str):
                    parts = ts_str.split(':')
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

                segments.append({
                    "start_time": round(parse_time(start_str), 2),
                    "end_time": round(parse_time(end_str), 2),
                    "text": text,
                    "speaker": "Instructor",
                    "segment_index": idx
                })
            full_text = " ".join(s["text"] for s in segments)
            return {
                "provider": "Uploaded Subtitles (SRT)",
                "full_text": full_text,
                "word_count": len(full_text.split()),
                "duration": segments[-1]["end_time"] if segments else target_duration,
                "segments": segments
            }

        # Check if VTT format (00:01.000 --> 00:04.000 or 00:00:01.000 --> 00:00:04.000)
        vtt_pattern = re.compile(
            r'(?:(\d{2}:)?\d{2}:\d{2}\.\d{3})\s*-->\s*(?:(\d{2}:)?\d{2}:\d{2}\.\d{3})\s*\n(.*?)(?=\n\s*(?:(?:\d{2}:)?\d{2}:\d{2}\.\d{3})\s*-->|\Z)',
            re.DOTALL
        )
        vtt_matches = list(vtt_pattern.finditer(raw_text))
        if vtt_matches and len(vtt_matches) >= 2:
            segments = []
            for idx, match in enumerate(vtt_matches):
                lines = match.group(0).split('\n')
                ts_line = lines[0]
                text = " ".join(" ".join(lines[1:]).strip().split())
                ts_parts = ts_line.split('-->')

                def parse_vtt_time(s):
                    s = s.strip()
                    parts = s.split(':')
                    if len(parts) == 3:
                        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                    return float(parts[0]) * 60 + float(parts[1])

                s_time = parse_vtt_time(ts_parts[0])
                e_time = parse_vtt_time(ts_parts[1])
                segments.append({
                    "start_time": round(s_time, 2),
                    "end_time": round(e_time, 2),
                    "text": text,
                    "speaker": "Instructor",
                    "segment_index": idx
                })
            full_text = " ".join(s["text"] for s in segments)
            return {
                "provider": "Uploaded Subtitles (VTT)",
                "full_text": full_text,
                "word_count": len(full_text.split()),
                "duration": segments[-1]["end_time"] if segments else target_duration,
                "segments": segments
            }

        # Plain text: Split into sentences and distribute evenly across detected media duration
        clean_text = raw_text.strip()
        sentence_delimiters = re.compile(r'(?<=[.!?])\s+')
        sentences = [s.strip() for s in sentence_delimiters.split(clean_text) if len(s.strip()) > 5]

        if not sentences:
            sentences = [clean_text]

        chunk_size = 2 if len(sentences) <= 8 else 3
        chunks = []
        for i in range(0, len(sentences), chunk_size):
            chunks.append(" ".join(sentences[i:i + chunk_size]))

        if not chunks:
            chunks = [clean_text]

        step = target_duration / len(chunks)
        segments = []
        for idx, chunk in enumerate(chunks):
            s_time = round(idx * step, 1)
            e_time = round((idx + 1) * step, 1) if idx < len(chunks) - 1 else round(target_duration, 1)
            segments.append({
                "start_time": s_time,
                "end_time": e_time,
                "text": chunk,
                "speaker": "Instructor",
                "segment_index": idx
            })

        full_text = " ".join(s["text"] for s in segments)
        return {
            "provider": "Uploaded Transcript Notes",
            "full_text": full_text,
            "word_count": len(full_text.split()),
            "duration": target_duration,
            "segments": segments
        }

transcription_service = TranscriptionService()
