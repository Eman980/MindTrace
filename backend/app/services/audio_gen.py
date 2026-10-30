import os
import wave
import struct
import math

def generate_sample_audio_if_needed(output_path: str, duration_seconds: int = 420):
    """
    Generates a valid, playable PCM WAV audio file with pleasant lecture-like chime/tone pulses
    if it does not already exist, so the HTML5 media player plays actual audio with seek/replay support!
    """
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Audio parameters
    sample_rate = 8000  # 8kHz mono is tiny and ultra-fast to generate
    num_samples = sample_rate * min(duration_seconds, 60) # Generate 60s looping audio or 420s
    
    with wave.open(output_path, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            # Create gentle voice-like modulation and chord pulses
            pulse = (math.sin(2 * math.pi * 0.5 * t) + 1.0) * 0.5
            freq = 220.0 + 40.0 * math.sin(2 * math.pi * 0.2 * t)
            value = int(32767.0 * 0.15 * pulse * math.sin(2 * math.pi * freq * t))
            data = struct.pack("<h", value)
            wav_file.writeframesraw(data)
            
    return output_path
