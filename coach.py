import os
import sys
import base64
import argparse
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sarvamai import SarvamAI

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

# Load environment variables
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

def transcribe_audio(audio_path: Path) -> str:
    """Transcribes reference audio using Saaras v3."""
    print(f"\n[Transcribe] Listening to '{audio_path.name}' with Saaras v3...")
    with open(audio_path, "rb") as f:
        resp = client.speech_to_text.transcribe(
            file=f,
            model="saaras:v3",
        )
    transcript = resp.transcript.strip()
    print(f" -> Heard from your audio: \"{transcript}\"")
    return transcript

def translate_text(text: str, target_lang: str) -> str:
    """Translates text into target Indian language using Mayura."""
    print(f"\n[Translate] Translating with Mayura to {SUPPORTED_LANGUAGES.get(target_lang, target_lang)}...")
    resp = client.text.translate(
        input=text,
        source_language_code="auto",
        target_language_code=target_lang,
        mode="modern-colloquial",
    )
    translated = resp.translated_text.strip()
    print(f" -> Translation: \"{translated}\"")
    return translated

def get_phonetic_and_tips(native_phrase: str, lang_name: str, english_meaning: str = "", notation_mode: str = "all") -> str:
    """Uses Sarvam-105B to give phonetic transcription (IPA / IAST / Roman) and articulatory mouth placement tips."""
    prompt = (
        f"You are an expert Indic language phonetician and pronunciation coach for {lang_name}.\n"
        f"Target Phrase: '{native_phrase}'"
    )
    if english_meaning:
        prompt += f" (Meaning: '{english_meaning}')\n"

    fields = []
    if notation_mode in ("iast", "all"):
        fields.append("IAST: <Precise IAST transliteration with accurate diacritics like ā, ī, ū, ṛ, ṭ, ḍ, ṇ, ś, ṣ, ṃ, ḥ>")
    if notation_mode in ("ipa", "all"):
        fields.append("IPA: <Precise International Phonetic Alphabet transcription enclosed in /.../, indicating dental vs retroflex consonants and Indic vowels>")
    if notation_mode in ("roman", "all"):
        fields.append("SYLLABLES: <Casual hyphenated syllable-by-syllable pronunciation breakdown>")
    fields.append("TIP: <1-2 concise sentences on articulatory phonetics, tongue/lip positioning, aspiration, and stress>")

    prompt += "\nOutput in this exact format:\n" + "\n".join(fields)

    resp = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()

def generate_topic_lesson(lang_name: str, topic: str = "travel") -> tuple[str, str]:
    """Generates a contextual, non-trivial phrase for a specific topic with Sarvam-105B."""
    print(f"\n[AI Coach] Generating situational phrase for topic: '{topic}' in {lang_name}...")
    prompt = (
        f"You are an Indic language coach for {lang_name}.\n"
        f"Create ONE realistic, practical conversational sentence for the situation: '{topic}'.\n"
        "Do NOT use trivial greetings like 'Hello' or 'How are you'.\n"
        "Format exactly as:\n"
        "PHRASE_NATIVE: <sentence in native script>\n"
        "PHRASE_ENGLISH: <English meaning>"
    )
    resp = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
    )
    content = resp.choices[0].message.content.strip()
    native_phrase = ""
    english_meaning = ""
    for line in content.splitlines():
        if line.startswith("PHRASE_NATIVE:"):
            native_phrase = line.replace("PHRASE_NATIVE:", "").strip()
        elif line.startswith("PHRASE_ENGLISH:"):
            english_meaning = line.replace("PHRASE_ENGLISH:", "").strip()
    
    if not native_phrase:
        native_phrase = content
    return native_phrase, english_meaning

def main():
    parser = argparse.ArgumentParser(description="Language Coach with Your Own Voice (Powered by Sarvam AI)")
    parser.add_argument(
        "--lang",
        default="bn-IN",
        choices=list(SUPPORTED_LANGUAGES.keys()),
        help="Target language code (e.g. bn-IN, hi-IN, ta-IN, te-IN, kn-IN, mr-IN, gu-IN)",
    )
    parser.add_argument(
        "--text",
        default=None,
        help="English (or any) text to translate into target language and pronounce in your voice",
    )
    parser.add_argument(
        "--from-audio",
        action="store_true",
        help="Transcribe the reference audio with Saaras v3, translate it, and clone it in the target language",
    )
    parser.add_argument(
        "--phrase",
        default=None,
        help="Direct phrase in native script (skips translation)",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="Topic for AI-generated situational phrase (e.g., travel, restaurant, directions, bargaining, emergency)",
    )
    parser.add_argument(
        "--notation",
        "--phonetic",
        dest="notation",
        default="all",
        choices=["all", "ipa", "iast", "roman"],
        help="Phonetic notation format: 'ipa' (IPA), 'iast' (IAST transliteration), 'roman' (casual syllables), or 'all' (default)",
    )
    parser.add_argument(
        "--ref",
        default="reference.wav",
        help="Path to learner's reference audio WAV file",
    )
    parser.add_argument(
        "--out",
        default="coached_pronunciation.wav",
        help="Output audio path for the synthesized voice file",
    )
    args = parser.parse_args()

    lang_code = args.lang
    lang_name = SUPPORTED_LANGUAGES.get(lang_code, lang_code)
    ref_file = Path(args.ref).resolve()
    ref_audio_path = get_or_create_reference_audio(ref_file)

    print("=" * 65)
    print("Sarvam AI - Language Coach With Your Own Voice")
    print("=" * 65)
    print(f"Target Language: {lang_name} ({lang_code})")
    print(f"Learner Voice Reference: {ref_audio_path.name}")

    target_phrase = ""
    source_english = ""

    # Mode 1: Direct native phrase
    if args.phrase:
        target_phrase = args.phrase
        print(f"\n[Input] Using direct phrase: \"{target_phrase}\"")

    # Mode 2: Translate text provided via CLI
    elif args.text:
        source_english = args.text
        print(f"\n[Input] English text: \"{source_english}\"")
        target_phrase = translate_text(source_english, lang_code)

    # Mode 3: Transcribe reference audio & translate
    elif args.from_audio:
        heard_text = transcribe_audio(ref_audio_path)
        source_english = heard_text
        target_phrase = translate_text(heard_text, lang_code)

    # Mode 4: Topic-based phrase
    elif args.topic:
        target_phrase, source_english = generate_topic_lesson(lang_name, args.topic)

    # Interactive prompt if no arguments were specified
    else:
        print("\nChoose an option:")
        print("  1. Translate your reference audio recording into " + lang_name)
        print("  2. Type your own English text to translate & hear in your voice")
        print("  3. AI Coach: Situational lesson (travel, dining, asking directions, etc.)")
        try:
            choice = input("\nEnter choice [1, 2, or 3] (default 1): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "1"

        if choice == "2":
            try:
                user_text = input("Enter English sentence: ").strip()
            except (EOFError, KeyboardInterrupt):
                user_text = "Where is the nearest train station?"
            if not user_text:
                user_text = "Where is the nearest train station?"
            source_english = user_text
            target_phrase = translate_text(source_english, lang_code)
        elif choice == "3":
            try:
                topic = input("Enter topic (e.g. travel, food, directions, shopping): ").strip()
            except (EOFError, KeyboardInterrupt):
                topic = "travel"
            if not topic:
                topic = "travel"
            target_phrase, source_english = generate_topic_lesson(lang_name, topic)
        else:
            heard_text = transcribe_audio(ref_audio_path)
            source_english = heard_text
            target_phrase = translate_text(heard_text, lang_code)

    # Step 2: Get Pronunciation Guidance from Sarvam-105B
    print(f"\n[Coach] Generating phonetic guide ({args.notation.upper()}) & pronunciation tips with Sarvam-105B...")
    coaching_tips = get_phonetic_and_tips(target_phrase, lang_name, source_english, notation_mode=args.notation)
    print("\n" + "-" * 40)
    print(f"Phrase in {lang_name}: {target_phrase}")
    if source_english:
        print(f"Meaning: {source_english}")
    print(coaching_tips)
    print("-" * 40)

    # Step 3: Instant Cross-Lingual Voice Cloning
    print(f"\n[Synthesis] Generating native {lang_name} speech in YOUR cloned voice...")
    output_audio_path = Path(args.out).resolve()

    with open(ref_audio_path, "rb") as f:
        voice_response = client.voice_cloning.convert(
            ref_audio=f,
            text=target_phrase,
            language_code=lang_code,
        )

    audio_bytes = base64.b64decode(voice_response.audio_b64 or voice_response.audio)
    with open(output_audio_path, "wb") as f:
        f.write(audio_bytes)

    print(f"\n[Success] Audio saved: {output_audio_path.name} ({len(audio_bytes):,} bytes)")
    print(f" -> Play '{output_audio_path.name}' to hear yourself speaking: \"{target_phrase}\"!")

if __name__ == "__main__":
    main()
