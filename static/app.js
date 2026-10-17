/**
 * Sarvam Language Coach - Frontend Studio Controller
 * Handles Voice Recording (Pure PCM WAV), Visualizer, Player, & Practice Lab
 */

// State Management
const state = {
  activeMode: "text",
  notation: "all",
  currentAudioUrl: null,
  currentAudio: null,
  isPlaying: false,
  playbackRate: 1.0,
  targetPhrase: "আপনি কি বলতে পারবেন, এটার price কত?",
  targetLang: "bn-IN",
  isRecordingVoice: false,
  isRecordingPractice: false,
  audioContext: null,
  mediaStream: null,
  processor: null,
  audioBuffers: [],
  sampleRate: 16000,
};

// DOM References
const langSelect = document.getElementById("langSelect");
const voiceStatusBadge = document.getElementById("voiceStatusBadge");
const voiceStatusText = document.getElementById("voiceStatusText");
const btnRecordVoice = document.getElementById("btnRecordVoice");
const btnRecordVoiceText = document.getElementById("btnRecordVoiceText");
const voiceFileInput = document.getElementById("voiceFileInput");
const refAudioPlayer = document.getElementById("refAudioPlayer");
const activeVoiceName = document.getElementById("activeVoiceName");
const recordingTimer = document.getElementById("recordingTimer");
const micVisualizer = document.getElementById("micVisualizer");

const modeTabs = document.querySelectorAll(".mode-tab");
const modePanels = document.querySelectorAll(".mode-panel");
const inputText = document.getElementById("inputText");
const customTopicInput = document.getElementById("customTopicInput");
const directPhraseText = document.getElementById("directPhraseText");
const topicChips = document.querySelectorAll(".topic-chip");
const quickChips = document.querySelectorAll(".chip");
const pillBtns = document.querySelectorAll(".pill-btn[data-notation]");

const btnGenerate = document.getElementById("btnGenerate");
const btnGenerateText = document.getElementById("btnGenerateText");
const genSpinner = document.getElementById("genSpinner");

const deckLangTag = document.getElementById("deckLangTag");
const displayNative = document.getElementById("displayNative");
const displayMeaning = document.getElementById("displayMeaning");
const btnPlayAudio = document.getElementById("btnPlayAudio");
const progressBar = document.getElementById("progressBar");
const progressFill = document.getElementById("progressFill");
const playerTime = document.getElementById("playerTime");
const btnSpeedToggle = document.getElementById("btnSpeedToggle");
const btnCopyText = document.getElementById("btnCopyText");

const cardIast = document.getElementById("cardIast");
const cardIpa = document.getElementById("cardIpa");
const cardSyllables = document.getElementById("cardSyllables");
const valIast = document.getElementById("valIast");
const valIpa = document.getElementById("valIpa");
const valSyllables = document.getElementById("valSyllables");
const valTip = document.getElementById("valTip");

const btnPracticeRecord = document.getElementById("btnPracticeRecord");
const practiceStatus = document.getElementById("practiceStatus");
const evalResult = document.getElementById("evalResult");
const scoreVal = document.getElementById("scoreVal");
const evalTranscript = document.getElementById("evalTranscript");
const evalFeedback = document.getElementById("evalFeedback");

// ============================================================================
// Initialization
// ============================================================================
document.addEventListener("DOMContentLoaded", async () => {
  setupModeTabs();
  setupTopicChips();
  setupQuickChips();
  setupNotationPills();
  setupAudioPlayer();
  setupRecordingEvents();
  setupPracticeLab();
  setupCopyButton();
  await checkVoiceStatus();

  // Enable practice button for starter phrase
  btnPracticeRecord.disabled = false;
  practiceStatus.textContent = "Ready: Press record and repeat the phrase";
});

// ============================================================================
// Mode & Input Controls
// ============================================================================
function setupModeTabs() {
  modeTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      modeTabs.forEach((t) => t.classList.remove("active"));
      modePanels.forEach((p) => p.classList.remove("active"));

      tab.classList.add("active");
      state.activeMode = tab.dataset.mode;
      document.getElementById(`panel-${state.activeMode}`).classList.add("active");
    });
  });
}

function setupTopicChips() {
  topicChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      topicChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      if (customTopicInput) customTopicInput.value = "";
    });
  });

  if (customTopicInput) {
    customTopicInput.addEventListener("input", () => {
      if (customTopicInput.value.trim()) {
        topicChips.forEach((c) => c.classList.remove("active"));
      }
    });
  }
}

function setupQuickChips() {
  quickChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      inputText.value = chip.dataset.phrase;
    });
  });
}

function setupNotationPills() {
  pillBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      pillBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.notation = btn.dataset.notation;
      applyNotationVisibility();
    });
  });
}

function applyNotationVisibility() {
  const mode = state.notation;
  if (mode === "all") {
    cardIast.style.display = "block";
    cardIpa.style.display = "block";
    cardSyllables.style.display = "block";
  } else if (mode === "iast") {
    cardIast.style.display = "block";
    cardIpa.style.display = "none";
    cardSyllables.style.display = "none";
  } else if (mode === "ipa") {
    cardIast.style.display = "none";
    cardIpa.style.display = "block";
    cardSyllables.style.display = "none";
  } else if (mode === "roman") {
    cardIast.style.display = "none";
    cardIpa.style.display = "none";
    cardSyllables.style.display = "block";
  }
}

function setupCopyButton() {
  btnCopyText.addEventListener("click", () => {
    const textToCopy = `${displayNative.textContent}\nMeaning: ${displayMeaning.textContent}\nIAST: ${valIast.textContent}\nIPA: ${valIpa.textContent}`;
    navigator.clipboard.writeText(textToCopy);
    btnCopyText.textContent = "✓";
    setTimeout(() => {
      btnCopyText.textContent = "📋";
    }, 1500);
  });
}

// ============================================================================
// Voice Model & Status
// ============================================================================
async function checkVoiceStatus() {
  try {
    const res = await fetch("/api/voice/status");
    const data = await res.json();
    if (data.enrolled) {
      voiceStatusText.textContent = "Voice Active";
      voiceStatusBadge.querySelector(".status-dot").classList.remove("idle");
      activeVoiceName.textContent = `${data.filename} (${(data.size_bytes / 1024).toFixed(0)} KB)`;
      refAudioPlayer.src = "/api/voice/audio";
    } else {
      voiceStatusText.textContent = "No Voice Enrolled";
      voiceStatusBadge.querySelector(".status-dot").classList.add("idle");
      activeVoiceName.textContent = "None (Click 'Record My Voice' to enroll)";
    }
  } catch (err) {
    console.error("Status check failed:", err);
  }
}

// ============================================================================
// Generation Pipeline
// ============================================================================
btnGenerate.addEventListener("click", async () => {
  btnGenerate.disabled = true;
  btnGenerateText.textContent = "Coaching in Your Voice...";
  genSpinner.classList.remove("hidden");

  let payload = {
    mode: state.activeMode,
    target_lang: langSelect.value,
    notation: state.notation,
  };

  if (state.activeMode === "text") {
    payload.input_text = inputText.value.trim() || "Hello, how are you?";
  } else if (state.activeMode === "situation") {
    const customTopic = customTopicInput ? customTopicInput.value.trim() : "";
    if (customTopic) {
      payload.topic = customTopic;
    } else {
      const activeChip = document.querySelector(".topic-chip.active");
      payload.topic = activeChip ? activeChip.dataset.topic : "travel";
    }
  } else if (state.activeMode === "direct") {
    payload.direct_phrase = directPhraseText.value.trim() || "আমি ভালো আছি";
  }

  try {
    const res = await fetch("/api/coach/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Generation failed");
    }

    const data = await res.json();
    renderLesson(data);
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    btnGenerate.disabled = false;
    btnGenerateText.textContent = "Generate in My Voice ✦";
    genSpinner.classList.add("hidden");
  }
});

function renderLesson(data) {
  state.targetPhrase = data.target_phrase;
  state.targetLang = data.lang_code;

  displayNative.textContent = data.target_phrase;
  displayMeaning.textContent = data.english_meaning || "Direct translation";
  deckLangTag.textContent = `${data.lang_name} (${data.lang_code})`;

  valIast.textContent = data.phonetics.iast || "(Not available)";
  valIpa.textContent = data.phonetics.ipa || "(Not available)";
  valSyllables.textContent = data.phonetics.syllables || "(Not available)";
  valTip.textContent = data.phonetics.tip || "Practice slowly and focus on vowel clarity.";

  applyNotationVisibility();

  // Load audio into player
  if (data.audio_base64) {
    loadAudio(data.audio_base64);
  }

  // Enable practice shadowing lab
  btnPracticeRecord.disabled = false;
  practiceStatus.textContent = "Ready: Press record and repeat the phrase";
  evalResult.classList.add("hidden");
}

// ============================================================================
// Custom Audio Player Controller
// ============================================================================
function setupAudioPlayer() {
  state.currentAudio = new Audio();

  state.currentAudio.addEventListener("timeupdate", () => {
    if (state.currentAudio.duration) {
      const pct = (state.currentAudio.currentTime / state.currentAudio.duration) * 100;
      progressFill.style.width = `${pct}%`;
      playerTime.textContent = `${formatTime(state.currentAudio.currentTime)} / ${formatTime(state.currentAudio.duration)}`;
    }
  });

  state.currentAudio.addEventListener("ended", () => {
    state.isPlaying = false;
    btnPlayAudio.textContent = "▶";
    progressFill.style.width = "0%";
  });

  btnPlayAudio.addEventListener("click", () => {
    if (!state.currentAudio.src) return;
    if (state.isPlaying) {
      state.currentAudio.pause();
      state.isPlaying = false;
      btnPlayAudio.textContent = "▶";
    } else {
      state.currentAudio.playbackRate = state.playbackRate;
      state.currentAudio.play();
      state.isPlaying = true;
      btnPlayAudio.textContent = "❚❚";
    }
  });

  btnSpeedToggle.addEventListener("click", () => {
    if (state.playbackRate === 1.0) {
      state.playbackRate = 0.75;
      btnSpeedToggle.textContent = "0.75x";
      btnSpeedToggle.classList.add("active");
    } else {
      state.playbackRate = 1.0;
      btnSpeedToggle.textContent = "1.0x";
      btnSpeedToggle.classList.remove("active");
    }
    if (state.currentAudio) {
      state.currentAudio.playbackRate = state.playbackRate;
    }
  });

  progressBar.addEventListener("click", (e) => {
    if (!state.currentAudio.duration) return;
    const rect = progressBar.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    state.currentAudio.currentTime = pos * state.currentAudio.duration;
  });
}

function loadAudio(audioSrc) {
  state.currentAudio.src = audioSrc;
  state.currentAudio.playbackRate = state.playbackRate;
  state.isPlaying = true;
  btnPlayAudio.textContent = "❚❚";
  state.currentAudio.play().catch(() => {
    state.isPlaying = false;
    btnPlayAudio.textContent = "▶";
  });
}

function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

// ============================================================================
// Pure PCM 16-bit 16kHz WAV Recorder (Zero External Dependencies)
// ============================================================================
async function startMicCapture(onDataChunk) {
  state.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = state.audioContext.createMediaStreamSource(state.mediaStream);

  // Use ScriptProcessorNode to capture PCM samples
  state.processor = state.audioContext.createScriptProcessor(4096, 1, 1);
  state.audioBuffers = [];

  state.processor.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0);
    // clone channel buffer
    state.audioBuffers.push(new Float32Array(input));
    if (onDataChunk) onDataChunk(input);
  };

  source.connect(state.processor);
  state.processor.connect(state.audioContext.destination);

  startVisualizer(source, state.audioContext);
}

function stopMicCapture() {
  if (state.processor) {
    state.processor.disconnect();
    state.processor = null;
  }
  if (state.mediaStream) {
    state.mediaStream.getTracks().forEach((track) => track.stop());
    state.mediaStream = null;
  }
  if (state.audioContext) {
    const originalRate = state.audioContext.sampleRate;
    state.audioContext.close();
    state.audioContext = null;

    // Merge Float32 buffers and resample to 16kHz
    const merged = mergeBuffers(state.audioBuffers);
    const downsampled = downsampleBuffer(merged, originalRate, 16000);
    const wavBlob = encodeWAV(downsampled, 16000);
    return wavBlob;
  }
  return null;
}

function mergeBuffers(bufferList) {
  let length = 0;
  bufferList.forEach((b) => (length += b.length));
  const result = new Float32Array(length);
  let offset = 0;
  bufferList.forEach((b) => {
    result.set(b, offset);
    offset += b.length;
  });
  return result;
}

function downsampleBuffer(buffer, sampleRate, outSampleRate) {
  if (outSampleRate === sampleRate) return buffer;
  const ratio = sampleRate / outSampleRate;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0, count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = count ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  /* RIFF identifier */
  writeString(view, 0, "RIFF");
  /* file length */
  view.setUint32(4, 36 + samples.length * 2, true);
  /* RIFF type */
  writeString(view, 8, "WAVE");
  /* format chunk identifier */
  writeString(view, 12, "fmt ");
  /* format chunk length */
  view.setUint32(16, 16, true);
  /* sample format (raw) */
  view.setUint16(20, 1, true);
  /* channel count */
  view.setUint16(22, 1, true);
  /* sample rate */
  view.setUint32(24, sampleRate, true);
  /* byte rate (sample rate * block align) */
  view.setUint32(28, sampleRate * 2, true);
  /* block align (channel count * bytes per sample) */
  view.setUint16(32, 2, true);
  /* bits per sample */
  view.setUint16(34, 16, true);
  /* data chunk identifier */
  writeString(view, 36, "data");
  /* data chunk length */
  view.setUint32(40, samples.length * 2, true);

  // Write PCM 16-bit samples
  let index = 44;
  for (let i = 0; i < samples.length; i++, index += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(index, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: "audio/wav" });
}

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

// Canvas Visualizer
let visualizerAnimationId = null;
function startVisualizer(source, ctx) {
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 64;
  source.connect(analyser);

  const canvasCtx = micVisualizer.getContext("2d");
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    visualizerAnimationId = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);

    canvasCtx.fillStyle = "#121211";
    canvasCtx.fillRect(0, 0, micVisualizer.width, micVisualizer.height);

    const barWidth = (micVisualizer.width / bufferLength) * 1.5;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const barHeight = (dataArray[i] / 255) * micVisualizer.height * 0.85;
      canvasCtx.fillStyle = "#D97757";
      canvasCtx.fillRect(x, micVisualizer.height - barHeight, barWidth - 2, barHeight);
      x += barWidth;
    }
  }
  draw();
}

function stopVisualizer() {
  if (visualizerAnimationId) {
    cancelAnimationFrame(visualizerAnimationId);
    visualizerAnimationId = null;
  }
  const canvasCtx = micVisualizer.getContext("2d");
  canvasCtx.clearRect(0, 0, micVisualizer.width, micVisualizer.height);
}

// ============================================================================
// Voice Enrollment Recording
// ============================================================================
function setupRecordingEvents() {
  let timerInterval = null;
  let seconds = 0;

  btnRecordVoice.addEventListener("click", async () => {
    if (!state.isRecordingVoice) {
      try {
        await startMicCapture();
        state.isRecordingVoice = true;
        btnRecordVoice.classList.add("btn-terracotta");
        btnRecordVoiceText.textContent = "Stop & Save Voice";
        recordingTimer.classList.remove("hidden");
        seconds = 0;
        timerInterval = setInterval(() => {
          seconds++;
          const m = String(Math.floor(seconds / 60)).padStart(2, "0");
          const s = String(seconds % 60).padStart(2, "0");
          recordingTimer.textContent = `${m}:${s}`;
        }, 1000);
      } catch (err) {
        alert("Microphone access denied: " + err.message);
      }
    } else {
      // Stop and upload
      const wavBlob = stopMicCapture();
      stopVisualizer();
      clearInterval(timerInterval);
      recordingTimer.classList.add("hidden");
      state.isRecordingVoice = false;
      btnRecordVoice.classList.remove("btn-terracotta");
      btnRecordVoiceText.textContent = "Uploading...";

      if (wavBlob) {
        const formData = new FormData();
        formData.append("file", wavBlob, "reference.wav");

        try {
          const res = await fetch("/api/voice/enroll", {
            method: "POST",
            body: formData,
          });
          const result = await res.json();
          await checkVoiceStatus();
          btnRecordVoiceText.textContent = "Record My Voice";
          alert("✓ Voice successfully enrolled! Model is ready for cross-lingual cloning.");
        } catch (err) {
          alert("Upload failed: " + err.message);
          btnRecordVoiceText.textContent = "Record My Voice";
        }
      }
    }
  });

  // File Upload fallback
  voiceFileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      await fetch("/api/voice/enroll", {
        method: "POST",
        body: formData,
      });
      await checkVoiceStatus();
      alert("✓ Voice audio file uploaded and enrolled!");
    } catch (err) {
      alert("Upload failed: " + err.message);
    }
  });
}

// ============================================================================
// Shadowing Practice & Accuracy Scoring Lab
// ============================================================================
function setupPracticeLab() {
  btnPracticeRecord.addEventListener("click", async () => {
    if (!state.isRecordingPractice) {
      try {
        await startMicCapture();
        state.isRecordingPractice = true;
        btnPracticeRecord.textContent = "■ Stop & Evaluate Attempt";
        btnPracticeRecord.classList.add("btn-primary");
        practiceStatus.textContent = "Speaking... repeat the phrase clearly";
      } catch (err) {
        alert("Microphone error: " + err.message);
      }
    } else {
      const wavBlob = stopMicCapture();
      stopVisualizer();
      state.isRecordingPractice = false;
      btnPracticeRecord.textContent = "Evaluating...";
      btnPracticeRecord.disabled = true;
      practiceStatus.textContent = "Saaras v3 transcribing & evaluating pronunciation...";

      if (wavBlob) {
        const formData = new FormData();
        formData.append("file", wavBlob, "attempt.wav");
        formData.append("target_phrase", state.targetPhrase);
        formData.append("target_lang", state.targetLang);

        try {
          const res = await fetch("/api/coach/evaluate", {
            method: "POST",
            body: formData,
          });
          const data = await res.json();

          // Render score
          scoreVal.textContent = data.accuracy;
          evalTranscript.textContent = `"${data.spoken_transcript || "(No speech detected)"}"`;
          evalFeedback.textContent = data.feedback;
          evalResult.classList.remove("hidden");
        } catch (err) {
          alert("Evaluation error: " + err.message);
        } finally {
          btnPracticeRecord.disabled = false;
          btnPracticeRecord.textContent = "🎙 Record Your Attempt";
          btnPracticeRecord.classList.remove("btn-primary");
          practiceStatus.textContent = "Try again to improve your score";
        }
      }
    }
  });
}
