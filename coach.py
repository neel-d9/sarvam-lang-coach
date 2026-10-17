import os
import sys
import base64
import argparse
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sarvamai import SarvamAI

# Supported languages for Instant Voice Cloning
SUPPORTED_LANGUAGES = {
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "bn-IN": "Bengali",
    "kn-IN": "Kannada",
    "mr-IN": "Marathi",
    "gu-IN": "Gujarati",
    "pa-IN": "Punjabi",
    "ml-IN": "Malayalam",
    "od-IN": "Odia",
    "en-IN": "Indian English",
}

# 1. Load environment variables
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_file)
    except ImportError:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise ValueError("SARVAM_API_KEY is not set. Please add it to your .env file.")

client = SarvamAI(api_subscription_key=api_key)

def get_or_create_reference_audio(ref_path: Path) -> Path:
    """Uses existing reference audio or synthesizes a clean 10s sample using Bulbul TTS."""
    if ref_path.exists() and ref_path.stat().st_size > 1000:
        print(f"[Voice] Using existing reference audio: {ref_path}")
        return ref_path

    print(f"[Voice] '{ref_path.name}' not found. Synthesizing a sample clip using Bulbul TTS...")
    sample_text = (
        "Hello! I am excited to learn new languages. "
        "Every day is a great opportunity to practice pronunciation and discover new cultures."
    )
    tts_response = client.text_to_speech.convert(
        text=sample_text,
        language_code="en-IN",
        speaker="kavya",
        model="bulbul:v3",
    )
    
    audio_data = tts_response.audios[0]
    with open(ref_path, "wb") as f:
        f.write(base64.b64decode(audio_data))
    print(f"[Voice] Sample reference created at: {ref_path}")
    return ref_path

def main():
    parser = argparse.ArgumentParser(description="Language Coach with Your Own Voice (Powered by Sarvam AI)")
    parser.add_argument(
        "--lang",
        default="hi-IN",
        choices=list(SUPPORTED_LANGUAGES.keys()),
        help="Target language code (e.g. hi-IN, ta-IN, te-IN, bn-IN, kn-IN, mr-IN, gu-IN)",
    )
    parser.add_argument(
        "--phrase",
        default=None,
        help="Specific phrase to synthesize in native script (if omitted, Sarvam-105B will coach a new phrase)",
    )
    parser.add_argument(
        "--ref",
        default="reference.wav",
        help="Path to learner's reference audio WAV file (defaults to reference.wav)",
    )
    parser.add_argument(
        "--out",
        default="coached_pronunciation.wav",
        help="Output audio path for the synthesized voice file",
    )
    args = parser.parse_args()

    lang_code = args.lang
    lang_name = SUPPORTED_LANGUAGES.get(lang_code, lang_code)

    print("=" * 65)
    print("Sarvam AI - Language Coach With Your Own Voice")
    print("=" * 65)
    print(f"Target Language: {lang_name} ({lang_code})")

    # Step 1: AI Coach Curriculum Generation
    if args.phrase:
        native_phrase = args.phrase
        print(f"\n[1/3] Using custom phrase: {native_phrase}")
    else:
        print(f"\n[1/3] Sarvam-105B generating a tailored beginner lesson in {lang_name}...")
        prompt = (
            f"You are an Indic language pronunciation coach. Provide ONE beginner practical phrase in {lang_name}.\n"
            "Output in this exact format:\n"
            "PHRASE_NATIVE: <phrase in native script>\n"
            "PHRASE_ENGLISH: <English meaning>\n"
            "PHONETIC: <Romanized pronunciation breakdown>\n"
            "TIP: <1 sentence tip on pronunciation or mouth placement>"
        )
        chat_resp = client.chat.completions(
            model="sarvam-105b-conversations",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        coach_text = chat_resp.choices[0].message.content.strip()
        print("\n--- Lesson Details ---")
        print(coach_text)
        print("----------------------")

        native_phrase = "नमस्ते"
        for line in coach_text.splitlines():
            if line.startswith("PHRASE_NATIVE:"):
                parsed = line.replace("PHRASE_NATIVE:", "").strip()
                if parsed:
                    native_phrase = parsed

    # Step 2: Reference Voice File
    ref_file = Path(args.ref).resolve()
    ref_audio_path = get_or_create_reference_audio(ref_file)

    # Step 3: Instant Cross-Lingual Voice Cloning
    print(f"\n[2/3] Cloning learner voice into native {lang_name} pronunciation...")
    output_audio_path = Path(args.out).resolve()

    with open(ref_audio_path, "rb") as f:
        voice_response = client.voice_cloning.convert(
            ref_audio=f,
            text=native_phrase,
            language_code=lang_code,
        )

    audio_bytes = base64.b64decode(voice_response.audio_b64 or voice_response.audio)
    with open(output_audio_path, "wb") as f:
        f.write(audio_bytes)

    print(f"\n[3/3] Success! Audio generated:")
    print(f" -> Output File: {output_audio_path}")
    print(f" -> Size: {len(audio_bytes):,} bytes")
    print(f" -> Spoken Phrase: '{native_phrase}'")
    print("\nPlay the audio file to hear your own voice speaking with authentic native pronunciation!")

if __name__ == "__main__":
    main()
