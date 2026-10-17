# 🗣️ Language Coach with Your Own Voice

> **Hear yourself speak any Indian language with authentic native pronunciation.** Powered by [Sarvam AI](https://www.sarvam.ai/).

---

## 💡 Concept

Traditional language apps force learners to listen to generic voice actors. For many learners, this feels unnatural, intimidating, and distant.

**Language Coach with Your Own Voice** solves this by:
1. Taking a 10–15s reference recording of the learner speaking in their native language or English.
2. Generating authentic pronunciation of new vocabulary, phrases, and tongue-twisters **in the learner's own cloned voice**.
3. Providing real-time pedagogical tips on tongue placement, aspirated consonants, and phonetic breakdowns using `sarvam-105b-conversations`.

---

## 🚀 Sarvam AI APIs Used

- **Instant Voice Cloning (`client.voice_cloning`)**:
  - Leverages cross-lingual voice cloning across 11+ Indian languages (`hi-IN`, `ta-IN`, `te-IN`, `bn-IN`, `kn-IN`, `mr-IN`, `gu-IN`, `pa-IN`, `ml-IN`, `od-IN`).
  - Synthesizes authentic native Indic phonetics while retaining the user's vocal identity.
- **Chat Completion (`sarvam-105b-conversations`)**:
  - Acts as the personalized pronunciation coach, generating beginner-to-advanced lessons, phonetic breakdowns, and mouth/tongue tips.
- **Text-to-Speech (`Bulbul v3`)**:
  - Fallback and benchmark voice generation.
- **Speech-to-Text (`Saaras v3`)**:
  - Transcribes and evaluates learner imitation attempts.

---

## 🛠️ Setup & Installation

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/neel-d9/sarvam-lang-coach.git
cd sarvam-lang-coach
pip install -r requirements.txt
```

### 2. Configure API Key
Create a `.env` file in the root directory:
```env
SARVAM_API_KEY=your_sarvam_api_key_here
```

---

## ⚡ Quickstart

### Run the Coach
Generate a tailored lesson and hear it in your voice:

```bash
# Default (Hindi)
python coach.py

# Tamil
python coach.py --lang ta-IN

# Telugu
python coach.py --lang te-IN

# Bengali
python coach.py --lang bn-IN

# Marathi
python coach.py --lang mr-IN

# Kannada
python coach.py --lang kn-IN
```

### Use Your Real Voice
Place a clean 10–15 second audio recording of your voice named `reference.wav` in the project directory, or pass `--ref`:
```bash
python coach.py --lang hi-IN --ref path/to/my_voice.wav
```

### Practice Specific Phrases
```bash
python coach.py --lang ta-IN --phrase "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?"
```
The output audio is generated and saved as `coached_pronunciation.wav`.
