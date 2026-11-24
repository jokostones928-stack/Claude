"""Generate narration (Kokoro TTS), scene/cue timing, and an ambient music bed.

Outputs (in build/): narration.wav, music.wav, data.js (scenes + timing for the renderer)
"""
import json, os, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, os.environ.get("BUILD", "build"))
SCENES_FILE = os.environ.get("SCENES", "scenes.json")
MODEL_DIR = os.environ.get("KOKORO_DIR", os.path.expanduser("~/tts"))
VOICE = os.environ.get("VOICE", "af_heart")
SPEED = float(os.environ.get("SPEED", "0.98"))
SR = 24000

SCENE_LEAD = float(os.environ.get("LEAD", "0.9"))   # silence before first cue of a scene
CUE_GAP = float(os.environ.get("GAP", "0.45"))     # pause between cues
SCENE_TAIL = float(os.environ.get("TAIL", "1.3"))   # hold after last cue before next scene
TAIL_OVERRIDE = json.loads(os.environ.get("TAIL_OVERRIDE", '{"title": 1.0, "takeaway": 2.0, "outro": 4.5}'))
LEAD_OVERRIDE = json.loads(os.environ.get("LEAD_OVERRIDE", '{"title": 1.6, "outro": 1.2}'))


def tts_all(scenes):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
    cache_dir = os.path.join(HERE, "build", "tts")
    os.makedirs(cache_dir, exist_ok=True)
    out = []
    for s in scenes:
        clips = []
        for i, text in enumerate(s["cues"]):
            key = f"{s['id']}_{i}"
            path = os.path.join(cache_dir, key + ".wav")
            txtp = path + ".txt"
            if os.path.exists(path) and open(txtp).read() == f"{VOICE}|{SPEED}|{text}":
                a, _ = sf.read(path, dtype="float32")
            else:
                print("TTS", key, flush=True)
                a, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
                assert sr == SR
                a = trim(a)
                sf.write(path, a, SR)
                open(txtp, "w").write(f"{VOICE}|{SPEED}|{text}")
            clips.append(a)
        out.append(clips)
    return out


def trim(a, thr=0.004):
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a
    s = max(0, idx[0] - int(0.03 * SR)); e = min(len(a), idx[-1] + int(0.08 * SR))
    return a[s:e]


def build_timeline(scenes, clips):
    t = 0.0
    pieces = []
    timing = []
    for s, cl in zip(scenes, clips):
        start = t
        t += LEAD_OVERRIDE.get(s["id"], SCENE_LEAD)
        cues = []
        for j, a in enumerate(cl):
            d = len(a) / SR
            cues.append({"start": round(t - start, 3), "dur": round(d, 3)})
            pieces.append((t, a))
            t += d + (CUE_GAP if j < len(cl) - 1 else 0)
        t += TAIL_OVERRIDE.get(s["id"], SCENE_TAIL)
        timing.append({"start": round(start, 3), "dur": round(t - start, 3), "cues": cues})
    total = t
    voice = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for st, a in pieces:
        i = int(st * SR); voice[i:i + len(a)] += a
    voice = voice / max(1e-6, np.abs(voice).max()) * 0.89
    return voice, timing, total


def music(total, sr=44100, seed=7):
    """Warm ambient pad + soft plucked arpeggio. Fully synthesized (royalty free)."""
    rng = np.random.default_rng(seed)
    n = int(total * sr)
    t = np.arange(n) / sr
    out = np.zeros((n, 2), dtype=np.float64)
    midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)
    # D major-ish warm progression: Dmaj7, Bm7, Gmaj7, A(sus)
    chords = [[50, 57, 61, 64, 66], [47, 54, 57, 62, 66], [43, 55, 59, 62, 66], [45, 52, 57, 61, 64]]
    bar = 8.0
    nb = int(np.ceil(total / bar)) + 1
    for b in range(nb):
        ch = chords[b % 4]
        s0 = b * bar - 1.5; s1 = s0 + bar + 3.0
        i0 = max(0, int(s0 * sr)); i1 = min(n, int(s1 * sr))
        if i1 <= i0:
            continue
        tt = t[i0:i1] - s0
        L = s1 - s0
        env = np.minimum(1, tt / 2.5) * np.minimum(1, (L - tt) / 2.5)
        env = np.clip(env, 0, 1) ** 1.5
        for k, m in enumerate(ch):
            f = midi(m)
            for det, pan in ((-0.12, 0.3), (0.12, 0.7)):
                ph = rng.uniform(0, 2 * np.pi)
                ff = f * 2 ** (det / 12 / 4)
                w = np.sin(2 * np.pi * ff * tt + ph) + 0.18 * np.sin(4 * np.pi * ff * tt + ph) + 0.06 * np.sin(6 * np.pi * ff * tt)
                amp = (0.05 if k == 0 else 0.032) * env
                out[i0:i1, 0] += w * amp * (1 - pan)
                out[i0:i1, 1] += w * amp * pan
    # plucked arpeggio (sparse, gentle)
    step = 0.5
    pattern = [0, 2, 3, 4, 3, 2, 1, 2]
    for si in range(int(total / step)):
        st = si * step
        if rng.random() < 0.35:
            continue
        ch = chords[int(st // bar) % 4]
        m = ch[pattern[si % len(pattern)] % len(ch)] + 12
        f = midi(m)
        dur = 2.2
        i0 = int(st * sr); i1 = min(n, i0 + int(dur * sr))
        tt = t[i0:i1] - st
        env = np.exp(-tt * 2.6) * np.minimum(1, tt / 0.004)
        w = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 4)) * env * 0.022
        pan = 0.5 + 0.35 * np.sin(si * 0.7)
        out[i0:i1, 0] += w * (1 - pan); out[i0:i1, 1] += w * pan
    # simple stereo feedback delay "reverb"
    for d, g in ((0.37, 0.35), (0.53, 0.28), (0.79, 0.2), (1.13, 0.14)):
        k = int(d * sr)
        out[k:, 0] += out[:-k, 1] * g * 0.6
        out[k:, 1] += out[:-k, 0] * g * 0.6
    # one-pole lowpass for warmth
    a = 0.25
    from scipy.signal import lfilter
    out = lfilter([a], [1, a - 1], out, axis=0)
    fade = np.minimum(1, t / 3.0) * np.minimum(1, (total - t) / 4.0)
    out *= np.clip(fade, 0, 1)[:, None]
    out = out / np.abs(out).max() * 0.9
    return out.astype(np.float32), sr


def main():
    os.makedirs(BUILD, exist_ok=True)
    scenes = json.load(open(os.path.join(HERE, SCENES_FILE)))
    clips = tts_all(scenes)
    voice, timing, total = build_timeline(scenes, clips)
    sf.write(os.path.join(BUILD, "narration.wav"), voice, SR)
    m, msr = music(total + 1)
    sf.write(os.path.join(BUILD, "music.wav"), m, msr)
    with open(os.path.join(BUILD, "data.js"), "w") as f:
        f.write("window.SCENES=" + json.dumps(scenes) + ";\n")
        f.write("window.TIMING=" + json.dumps(timing) + ";\n")
        f.write(f"window.TOTAL={total:.3f};\n")
    print(f"total duration: {total:.1f}s ({total/60:.1f} min)")


if __name__ == "__main__":
    main()
