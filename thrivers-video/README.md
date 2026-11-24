# Thrivers — Animated Book Summary

A narrated, fully animated 1080p explainer video of *Thrivers* by Michele Borba, Ed.D. (2021).

## Pipeline
1. **`scenes.json`**: the storyboard. Each scene has narration cues plus the on-screen content.
2. **`audio.py`** — narrates every cue with the Kokoro neural TTS (voice `af_heart`), times scenes to the speech, and synthesizes an original ambient music bed → `build/narration.wav`, `build/music.wav`, `build/data.js`.
3. **`index.html`** — the animation. `renderAt(t)` deterministically draws any moment, so every visual reveal is synced to its narration cue. Open `index.html?play` in a browser to preview (no audio).
4. **`render.js`** — drives headless Chromium frame-by-frame (30 fps, 4 parallel workers), encodes H.264 with ffmpeg, and mixes narration and music (with ducking) → `Thrivers_Book_Summary.mp4`.

## Setup
```bash
pip install kokoro-onnx soundfile scipy
mkdir -p ~/tts && cd ~/tts
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd - && npm install            # lucide-static icons; Playwright + ffmpeg required
python3 audio.py
node render.js                 # options: --workers 4 --fps 30 --from 0 --to 60 --still 10,20
```
Change the voice with `VOICE=am_michael python3 audio.py` (other Kokoro voices: `af_bella`, `bf_emma`, `bm_george`, and more).
