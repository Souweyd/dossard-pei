"""Bruitages synthétisés des stories vidéo (aucun fichier son externe, donc aucun droit à gérer).
sfx.track([(t, 'pop'), (t, 'whoosh', durée), ...], durée_totale, wav) puis sfx.mux(mp4, wav)."""
import subprocess, wave, pathlib
import numpy as np

SR = 44100
rng = np.random.default_rng(7)


def _env(n, a=.004, r=None):
    """short attack, exponential release"""
    t = np.arange(n) / SR
    att = np.clip(t / a, 0, 1)
    rel = np.exp(-t / (r or (n / SR / 4)))
    return att * rel


def pop(f=620, d=.12, v=.5):
    """soft bubble pop: falling sine"""
    n = int(d * SR); t = np.arange(n) / SR
    fr = f * (1.6 - .6 * t / d)
    return v * np.sin(2 * np.pi * np.cumsum(fr) / SR) * _env(n, .002, d / 5)


def tick(f=1800, d=.05, v=.25):
    n = int(d * SR); t = np.arange(n) / SR
    return v * np.sin(2 * np.pi * f * t) * _env(n, .001, d / 6)


def whoosh(d=1.0, v=.55, up=True):
    """filtered noise sweeping up (or down) in pitch, swelling then fading"""
    from scipy.signal import lfilter
    n = int(d * SR); x = rng.standard_normal(n)
    y = np.zeros(n); lo = .02 if up else .25
    hi = .25 if up else .02
    a = np.linspace(lo, hi, n)                       # one-pole low-pass, cutoff swept
    s = 0.
    for i in range(n):
        s += a[i] * (x[i] - s); y[i] = s
    y = lfilter([1, -1], [1, -.995], y)               # remove rumble
    w = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    y = y / (np.abs(y).max() + 1e-9)
    return v * y * w


def thud(d=.25, v=.6):
    """landing of the pin: low sine drop + tiny noise"""
    n = int(d * SR); t = np.arange(n) / SR
    fr = 160 * np.exp(-t * 9) + 55
    s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * _env(n, .002, .06)
    return v * s + .08 * rng.standard_normal(n) * _env(n, .001, .015)


def chime(v=.16):
    """two soft bell notes (end card)"""
    out = np.zeros(int(1.4 * SR))
    for k, (f, t0) in enumerate(((880, 0), (1318.5, .12))):
        n = int(1.2 * SR); t = np.arange(n) / SR
        s = (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * 2 * f * t)) * _env(n, .003, .35)
        i = int(t0 * SR); out[i:i + n] += v * s[:len(out) - i]
    return out


SOUNDS = dict(pop=pop, tick=tick, whoosh=whoosh, thud=thud, chime=chime)


def track(events, dur, wav):
    """events: (time, name, *args). Writes a 16-bit stereo wav."""
    buf = np.zeros(int(dur * SR) + SR)
    for t, name, *args in events:
        s = SOUNDS[name](*args); i = int(t * SR)
        buf[i:i + len(s)] += s[:len(buf) - i]
    buf = buf[:int(dur * SR)]
    peak = np.abs(buf).max()
    if peak > .9:
        buf *= .9 / peak
    pcm = (buf * 32767).astype('<i2')
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.repeat(pcm, 2).tobytes())


def mux(mp4, wav):
    """adds the sound to the video (video stream copied as is)"""
    mp4 = pathlib.Path(mp4); tmp = mp4.with_name('_snd_' + mp4.name)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp4), '-i', str(wav), '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', str(tmp)], check=True)
    tmp.replace(mp4)
