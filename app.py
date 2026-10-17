import os
import sys
import base64
import difflib
from pathlib import Path
from typing import Optional

# UTF-8 stdout on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sarvamai import SarvamAI

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

app = FastAPI(title="Sarvam Language Coach", version="1.0.0")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
REF_AUDIO_PATH = BASE_DIR / "reference.wav"

SUPPORTED_LANGUAGES = [
    {"code": "bn-IN", "name": "Bengali", "native": "বাংলা", "region": "Bengal & Tripura"},
    {"code": "hi-IN", "name": "Hindi", "native": "हिन्दी", "region": "North & Central India"},
    {"code": "ta-IN", "name": "Tamil", "native": "தமிழ்", "region": "Tamil Nadu"},
    {"code": "te-IN", "name": "Telugu", "native": "తెలుగు", "region": "Andhra Pradesh & Telangana"},
    {"code": "mr-IN", "name": "Marathi", "native": "मराठी", "region": "Maharashtra"},
    {"code": "kn-IN", "name": "Kannada", "native": "ಕನ್ನಡ", "region": "Karnataka"},
    {"code": "gu-IN", "name": "Gujarati", "native": "ગુજરાતી", "region": "Gujarat"},
    {"code": "pa-IN", "name": "Punjabi", "native": "ਪੰਜਾਬੀ", "region": "Punjab"},
    {"code": "ml-IN", "name": "Malayalam", "native": "മലയാളം", "region": "Kerala"},
    {"code": "od-IN", "name": "Odia", "native": "ଓଡ଼ିଆ", "region": "Odisha"},
    {"code": "en-IN", "name": "Indian English", "native": "English", "region": "Pan-India"},
]

class CoachRequest(BaseModel):
    mode: str = "text"  # text, audio, situation, direct
    input_text: Optional[str] = None
    target_lang: str = "bn-IN"
    topic: Optional[str] = "travel"
    direct_phrase: Optional[str] = None
    notation: str = "all"  # all, ipa, iast, roman

def parse_phonetic_fields(text: str) -> dict:
    data = {"iast": "", "ipa": "", "syllables": "", "tip": text}
    lines = text.splitlines()
    remaining_tip = []
    for line in lines:
        line_clean = line.strip()
        if line_clean.startswith("IAST:"):
            data["iast"] = line_clean.replace("IAST:", "").strip()
        elif line_clean.startswith("IPA:"):
            data["ipa"] = line_clean.replace("IPA:", "").strip()
        elif line_clean.startswith("SYLLABLES:"):
            data["syllables"] = line_clean.replace("SYLLABLES:", "").strip()
        elif line_clean.startswith("TIP:"):
            remaining_tip.append(line_clean.replace("TIP:", "").strip())
        else:
            remaining_tip.append(line_clean)
    if remaining_tip:
        data["tip"] = " ".join([l for l in remaining_tip if l]).strip()
    return data

@app.get("/api/languages")
async def get_languages():
    return SUPPORTED_LANGUAGES

@app.get("/api/voice/status")
async def get_voice_status():
    if REF_AUDIO_PATH.exists() and REF_AUDIO_PATH.stat().st_size > 1000:
        return {
            "enrolled": True,
            "filename": REF_AUDIO_PATH.name,
            "size_bytes": REF_AUDIO_PATH.stat().st_size,
        }
    return {"enrolled": False}

@app.get("/api/voice/audio")
async def get_voice_audio():
    if REF_AUDIO_PATH.exists():
        return FileResponse(REF_AUDIO_PATH, media_type="audio/wav")
    raise HTTPException(status_code=404, detail="No reference voice found")

@app.post("/api/voice/enroll")
async def enroll_voice(file: UploadFile = File(...)):
    """Uploads a WAV clip from the browser microphone to serve as the user's voice model."""
    content = await file.read()
    if len(content) < 1000:
        raise HTTPException(status_code=400, detail="Audio file too short. Please speak for at least 5 seconds.")

    with open(REF_AUDIO_PATH, "wb") as f:
        f.write(content)

    # Transcribe sample to confirm voice quality
    transcript = ""
    try:
        with open(REF_AUDIO_PATH, "rb") as f:
            stt = client.speech_to_text.transcribe(file=f, model="saaras:v3")
            transcript = stt.transcript.strip()
    except Exception as e:
        transcript = f"(Saved successfully. Transcription notice: {e})"

    return {
        "status": "success",
        "message": "Voice enrolled successfully",
        "size_bytes": len(content),
        "transcript": transcript,
    }

@app.post("/api/coach/generate")
async def generate_lesson(req: CoachRequest):
    lang_info = next((l for l in SUPPORTED_LANGUAGES if l["code"] == req.target_lang), None)
    lang_name = lang_info["name"] if lang_info else "Bengali"

    # Ensure reference audio exists
    if not REF_AUDIO_PATH.exists() or REF_AUDIO_PATH.stat().st_size < 1000:
        # Generate clean starter reference sample with Bulbul TTS
        sample_text = "Hello! I am excited to learn new languages. Every day is a great opportunity to practice."
        tts = client.text_to_speech.convert(
            text=sample_text,
            language_code="en-IN",
            speaker="kavya",
            model="bulbul:v3",
        )
        with open(REF_AUDIO_PATH, "wb") as f:
            f.write(base64.b64decode(tts.audios[0]))

    target_phrase = ""
    english_meaning = ""

    # Mode 1: Translate text
    if req.mode == "text":
        english_meaning = req.input_text or "Hello, how are you?"
        trans = client.text.translate(
            input=english_meaning,
            source_language_code="auto",
            target_language_code=req.target_lang,
            mode="modern-colloquial",
        )
        target_phrase = trans.translated_text.strip()

    # Mode 2: Transcribe reference audio & translate
    elif req.mode == "audio":
        with open(REF_AUDIO_PATH, "rb") as f:
            stt = client.speech_to_text.transcribe(file=f, model="saaras:v3")
        english_meaning = stt.transcript.strip()
        trans = client.text.translate(
            input=english_meaning,
            source_language_code="auto",
            target_language_code=req.target_lang,
            mode="modern-colloquial",
        )
        target_phrase = trans.translated_text.strip()

    # Mode 3: Situational topic phrase
    elif req.mode == "situation":
        topic = req.topic or "ordering street food"
        prompt = (
            f"You are an Indic language coach for {lang_name}.\n"
            f"Generate ONE practical, natural colloquial sentence for the situation: '{topic}'.\n"
            "Format exactly as:\n"
            "PHRASE_NATIVE: <native script phrase>\n"
            "PHRASE_ENGLISH: <English meaning>"
        )
        chat = client.chat.completions(
            model="sarvam-105b-conversations",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        content = chat.choices[0].message.content.strip()
        for line in content.splitlines():
            if line.startswith("PHRASE_NATIVE:"):
                target_phrase = line.replace("PHRASE_NATIVE:", "").strip()
            elif line.startswith("PHRASE_ENGLISH:"):
                english_meaning = line.replace("PHRASE_ENGLISH:", "").strip()
        if not target_phrase:
            target_phrase = content

    # Mode 4: Direct native phrase
    else:
        target_phrase = req.direct_phrase or "আমি ভালো আছি"
        english_meaning = req.input_text or ""

    # Generate Phonetics (IAST, IPA, Syllables, Tips) with Sarvam-105B
    phonetic_prompt = (
        f"You are an expert Indic language phonetician and pronunciation coach for {lang_name}.\n"
        f"Target Phrase: '{target_phrase}'"
    )
    if english_meaning:
        phonetic_prompt += f" (Meaning: '{english_meaning}')\n"
    phonetic_prompt += (
        "\nOutput in this exact format:\n"
        "IAST: <Precise IAST transliteration with accurate diacritics: ā, ī, ū, ṛ, ṭ, ḍ, ṇ, ś, ṣ, ṃ, ḥ>\n"
        "IPA: <Precise International Phonetic Alphabet transcription in /.../, indicating dental vs retroflex consonants>\n"
        "SYLLABLES: <Casual hyphenated syllable breakdown>\n"
        "TIP: <1-2 sentences on articulatory phonetics: mouth/tongue position, aspiration puff, and stress>"
    )

    p_chat = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": phonetic_prompt}],
        temperature=0.2,
    )
    phonetics = parse_phonetic_fields(p_chat.choices[0].message.content.strip())

    # Generate speech in learner's cloned voice
    with open(REF_AUDIO_PATH, "rb") as f:
        voice_resp = client.voice_cloning.convert(
            ref_audio=f,
            text=target_phrase,
            language_code=req.target_lang,
        )

    audio_b64 = voice_resp.audio_b64 or voice_resp.audio

    return {
        "target_phrase": target_phrase,
        "english_meaning": english_meaning,
        "lang_code": req.target_lang,
        "lang_name": lang_name,
        "phonetics": phonetics,
        "audio_base64": f"data:audio/wav;base64,{audio_b64}",
    }

@app.post("/api/coach/evaluate")
async def evaluate_attempt(
    file: UploadFile = File(...),
    target_phrase: str = Form(...),
    target_lang: str = Form(...),
):
    """Evaluates the learner's spoken attempt using Saaras v3 + alignment analysis."""
    content = await file.read()
    temp_attempt = BASE_DIR / "temp_attempt.wav"
    with open(temp_attempt, "wb") as f:
        f.write(content)

    # Transcribe with Saaras v3
    with open(temp_attempt, "rb") as f:
        stt = client.speech_to_text.transcribe(
            file=f,
            model="saaras:v3",
            language_code=target_lang,
        )
    spoken_transcript = stt.transcript.strip()

    # Calculate similarity ratio
    clean_target = "".join(target_phrase.split())
    clean_spoken = "".join(spoken_transcript.split())
    seq = difflib.SequenceMatcher(None, clean_target, clean_spoken)
    accuracy = int(seq.ratio() * 100)

    # Ask Sarvam-105B for constructive pedagogical feedback
    eval_prompt = (
        f"You are a gentle, encouraging language coach.\n"
        f"Target phrase: '{target_phrase}'\n"
        f"What the learner pronounced: '{spoken_transcript}'\n"
        f"Accuracy score: {accuracy}%\n"
        "Give 2 concise sentences of constructive feedback highlighting what sounded great and what specific syllable or sound to adjust."
    )
    fb_chat = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": eval_prompt}],
        temperature=0.3,
    )
    feedback = fb_chat.choices[0].message.content.strip()

    return {
        "accuracy": accuracy,
        "target_phrase": target_phrase,
        "spoken_transcript": spoken_transcript,
        "feedback": feedback,
    }

# Serve static frontend
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

