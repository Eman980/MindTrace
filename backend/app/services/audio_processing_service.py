import os
import shutil
import subprocess
import asyncio
from typing import Dict, Any, Optional, List, Tuple

class AudioProcessingService:
    """
    FFmpeg Acoustic Data Extraction & Audio Processing Pipeline.
    Handles multimedia file ingestion (MP4, MOV, WEBM, MP3, WAV, M4A, OGG),
    compressing audio to 64 kbps mono MP3, dynamically scaling timeouts,
    and splitting long recordings into ~10-minute timestamp-offset chunks.
    """

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> Optional[str]:
        path = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg")
        if path and os.path.exists(path):
            return path
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass
        return None

    def is_ffmpeg_available(self) -> bool:
        if not self.ffmpeg_path or not os.path.exists(self.ffmpeg_path):
            self.ffmpeg_path = self._find_ffmpeg()
        return self.ffmpeg_path is not None and os.path.exists(self.ffmpeg_path)

    def detect_media_duration(self, file_path: str) -> float:
        """
        Dynamically extracts exact media duration in seconds for uploaded
        multimedia files (MP4, MOV, WEBM, MP3, WAV, M4A, OGG).
        """
        if not os.path.exists(file_path):
            return 300.0

        ext = os.path.splitext(file_path)[1].lower()

        # 1. If FFprobe or FFmpeg is available on host, try fast probe first
        if self.is_ffmpeg_available():
            try:
                ffprobe_path = shutil.which("ffprobe") or os.path.join(os.path.dirname(self.ffmpeg_path), "ffprobe.exe")
                if os.path.exists(ffprobe_path):
                    proc = subprocess.run(
                        [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=15
                    )
                    if proc.returncode == 0:
                        val = float(proc.stdout.decode().strip())
                        if val > 0:
                            return round(val, 2)
            except Exception:
                pass

        # 2. WAV: Standard wave library
        if ext == ".wav":
            try:
                import wave
                with wave.open(file_path, "rb") as w:
                    frames = w.getnframes()
                    rate = w.getframerate()
                    if rate > 0:
                        return round(frames / float(rate), 2)
            except Exception:
                pass

        # 3. MP4 / MOV / M4A: Parse ISOBMFF mvhd box
        if ext in (".mp4", ".mov", ".m4a"):
            try:
                import struct
                with open(file_path, "rb") as f:
                    while True:
                        h = f.read(8)
                        if len(h) < 8:
                            break
                        size, btype = struct.unpack(">I4s", h)
                        if btype == b"moov":
                            moov = f.read(size - 8)
                            idx = moov.find(b"mvhd")
                            if idx != -1:
                                mvhd = moov[idx + 4:]
                                v = mvhd[0]
                                if v == 1:
                                    ts, dur = struct.unpack(">IQ", mvhd[20:32])
                                else:
                                    ts, dur = struct.unpack(">II", mvhd[12:20])
                                if ts > 0 and dur > 0:
                                    return round(dur / float(ts), 2)
                            break
                        elif size == 1:
                            size = struct.unpack(">Q", f.read(8))[0]
                            f.seek(size - 16, 1)
                        elif size == 0:
                            break
                        else:
                            f.seek(size - 8, 1)
            except Exception:
                pass

        # 4. OGG: Parse last OggS page granule position
        if ext == ".ogg":
            try:
                import struct
                with open(file_path, "rb") as f:
                    f.seek(0, 2)
                    fsize = f.tell()
                    seek_back = min(fsize, 65536)
                    f.seek(fsize - seek_back)
                    buf = f.read(seek_back)
                    last_pos = buf.rfind(b"OggS")
                    if last_pos != -1 and len(buf) >= last_pos + 14:
                        granule = struct.unpack("<Q", buf[last_pos + 6:last_pos + 14])[0]
                        f.seek(0)
                        first_page = f.read(256)
                        sample_rate = 48000.0
                        if b"vorbis" in first_page:
                            v_idx = first_page.find(b"vorbis")
                            if len(first_page) >= v_idx + 15:
                                r = struct.unpack("<I", first_page[v_idx + 11:v_idx + 15])[0]
                                if r > 0:
                                    sample_rate = float(r)
                        if granule > 0 and sample_rate > 0:
                            return round(granule / sample_rate, 2)
            except Exception:
                pass

        # 5. Fallback: file size estimation
        fsize = os.path.getsize(file_path)
        estimated = round(fsize / 32000.0, 1)
        return max(5.0, min(estimated, 7200.0))

    async def extract_acoustic_data(self, file_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Compresses incoming media to 64 kbps mono MP3 with scaled FFmpeg timeout.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Media file not found at: {file_path}")

        file_size = os.path.getsize(file_path)
        base_name, ext = os.path.splitext(os.path.basename(file_path))
        ext = ext.lower()

        if output_dir is None:
            output_dir = os.path.dirname(file_path)

        extracted_mp3_path = os.path.join(output_dir, f"{base_name}_compressed.mp3")
        detected_duration = self.detect_media_duration(file_path)

        # Scale FFmpeg timeout dynamically with duration (at least 300s)
        ffmpeg_timeout = max(300, int(detected_duration * 0.75) if detected_duration else 300)

        result: Dict[str, Any] = {
            "source_path": file_path,
            "filename": os.path.basename(file_path),
            "extension": ext,
            "format": "mp3",
            "file_size_bytes": file_size,
            "duration_seconds": detected_duration,
            "acoustic_extracted": False,
            "pipeline": "fallback_acoustic_extractor",
            "audio_path_for_stt": file_path,
            "metadata": {
                "container": "MP3",
                "sample_rate": 16000,
                "channels": 1,
                "bitrate": "64k",
                "duration_seconds": detected_duration
            }
        }

        if self.is_ffmpeg_available():
            try:
                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-i", file_path,
                    "-vn",                      # Disable video stream
                    "-acodec", "libmp3lame",    # High-quality MP3 encoder
                    "-ab", "64k",               # 64 kbps bitrate (~0.5 MB/min)
                    "-ar", "16000",             # 16 kHz sample rate ideal for speech STT
                    "-ac", "1",                 # Mono channel
                    extracted_mp3_path
                ]

                proc = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=ffmpeg_timeout
                )

                if proc.returncode == 0 and os.path.exists(extracted_mp3_path):
                    mp3_size = os.path.getsize(extracted_mp3_path)
                    result["acoustic_extracted"] = True
                    result["pipeline"] = "ffmpeg_mp3_compressed_pipeline"
                    result["audio_path_for_stt"] = extracted_mp3_path
                    result["extracted_mp3_path"] = extracted_mp3_path
                    result["metadata"]["acoustic_size_bytes"] = mp3_size
                    mp3_dur = self.detect_media_duration(extracted_mp3_path)
                    if mp3_dur and mp3_dur > 0:
                        result["duration_seconds"] = mp3_dur
                        result["metadata"]["duration_seconds"] = mp3_dur
                    print(f"[FFmpeg Pipeline] Compressed audio to 64kbps mono MP3 ({mp3_size} bytes): {extracted_mp3_path}")
                    return result
                else:
                    err_msg = proc.stderr.decode(errors="replace")[:300]
                    print(f"[FFmpeg Pipeline] FFmpeg compression returned code {proc.returncode}: {err_msg}")
            except Exception as e:
                print(f"[FFmpeg Pipeline] FFmpeg execution error ({e}), falling back to direct media path.")

        # If already an audio file and ffmpeg unavailable
        result["acoustic_extracted"] = True
        result["pipeline"] = "native_acoustic_pipeline"
        result["audio_path_for_stt"] = file_path
        return result

    def split_audio_into_chunks(
        self,
        audio_path: str,
        chunk_duration_sec: int = 600,
        total_duration: Optional[float] = None
    ) -> List[Tuple[str, float, float]]:
        """
        Splits an audio file into ~10-minute chunks.
        Returns a list of tuples: (chunk_file_path, offset_seconds, duration_seconds)
        """
        if not os.path.exists(audio_path):
            return []

        dur = total_duration or self.detect_media_duration(audio_path)
        file_size = os.path.getsize(audio_path)

        # If audio is already short (< 10 min) or small (< 20MB), return single chunk
        if dur <= chunk_duration_sec + 30 or file_size < 20 * 1024 * 1024:
            return [(audio_path, 0.0, dur)]

        base_dir = os.path.dirname(audio_path)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        chunks_dir = os.path.join(base_dir, f"{base_name}_chunks")
        os.makedirs(chunks_dir, exist_ok=True)

        chunks: List[Tuple[str, float, float]] = []

        if self.is_ffmpeg_available():
            try:
                # Segment audio quickly into chunks without re-encoding
                chunk_pattern = os.path.join(chunks_dir, "chunk_%03d.mp3")
                cmd = [
                    self.ffmpeg_path,
                    "-y",
                    "-i", audio_path,
                    "-f", "segment",
                    "-segment_time", str(chunk_duration_sec),
                    "-c", "copy",
                    chunk_pattern
                ]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
                if proc.returncode == 0:
                    created_files = sorted([
                        os.path.join(chunks_dir, f)
                        for f in os.listdir(chunks_dir)
                        if f.startswith("chunk_") and f.endswith(".mp3")
                    ])
                    running_offset = 0.0
                    for c_file in created_files:
                        c_dur = self.detect_media_duration(c_file)
                        chunks.append((c_file, round(running_offset, 2), round(c_dur, 2)))
                        running_offset += c_dur
                    if chunks:
                        print(f"[AudioSplit] Successfully split audio into {len(chunks)} chunks of ~{chunk_duration_sec}s.")
                        return chunks
            except Exception as e:
                print(f"[AudioSplit] FFmpeg segment failed ({e}), falling back to single file.")

        return [(audio_path, 0.0, dur)]

audio_processing_service = AudioProcessingService()
