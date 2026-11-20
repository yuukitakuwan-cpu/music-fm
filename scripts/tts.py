#!/usr/bin/env python3
"""台本テキストを VOICEVOX で女性ボイスの mp3 にする。

使い方:
    python3 scripts/tts.py script.txt out.mp3 [--speaker 8]

台本の書式:
    - 1行 = 1発話。空行 = 少し長めの間。
    - "#" で始まる行はコメント（読まない）。
    - "[jingle]" だけの行 = 短いチャイムを挟む（番組のコーナー区切り用）。

事前に scripts/setup_voicevox.sh でエンジンを起動しておくこと。
既定の声: 春日部つむぎ（ノーマル, style id 8）— 明るく元気な女の子の声。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import wave

HOST = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
# localhost にはプロキシを通さない
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

SPEAKER_DEFAULT = 8  # 春日部つむぎ ノーマル
RATE = 24000


def api(path, params=None, body=None):
    url = HOST + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with _opener.open(req, timeout=300) as r:
        return r.read()


def synth_line(text, speaker, speed, pitch, intonation):
    q = json.loads(api("/audio_query", {"text": text, "speaker": speaker}))
    q.update(speedScale=speed, pitchScale=pitch, intonationScale=intonation,
             volumeScale=1.0, prePhonemeLength=0.05, postPhonemeLength=0.1,
             outputSamplingRate=RATE, outputStereo=False)
    return api("/synthesis", {"speaker": speaker}, q)


def silence(sec):
    return b"\x00\x00" * int(RATE * sec)


def jingle_pcm():
    """ffmpeg で短い明るいチャイム（ド・ミ・ソ・ド）を生成"""
    notes = [523.25, 659.25, 783.99, 1046.5]
    expr = "+".join(
        f"0.22*sin(2*PI*{f}*t)*exp(-6*(t-{i*0.12}))*gte(t,{i*0.12})"
        for i, f in enumerate(notes))
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
         f"aevalsrc='{expr}':s={RATE}:d=1.2", "-ac", "1", "-f", "s16le", "-"],
        check=True, capture_output=True).stdout
    return out


def read_pcm(wav_bytes):
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        f.write(wav_bytes); f.flush()
        with wave.open(f.name) as w:
            assert w.getframerate() == RATE and w.getnchannels() == 1
            return w.readframes(w.getnframes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--speaker", type=int, default=SPEAKER_DEFAULT)
    ap.add_argument("--speed", type=float, default=1.12)
    ap.add_argument("--pitch", type=float, default=0.02)
    ap.add_argument("--intonation", type=float, default=1.25)
    ap.add_argument("--bitrate", default="96k")
    a = ap.parse_args()

    lines = open(a.script, encoding="utf-8").read().splitlines()
    pcm = bytearray()
    jingle = None
    n = sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))
    done = 0
    for raw in lines:
        line = raw.strip()
        if line.startswith("#"):
            continue
        if not line:
            pcm += silence(0.45)
            continue
        if line == "[jingle]":
            jingle = jingle or jingle_pcm()
            pcm += silence(0.2) + jingle + silence(0.3)
            done += 1
            continue
        pcm += read_pcm(synth_line(line, a.speaker, a.speed, a.pitch, a.intonation))
        pcm += silence(0.18)
        done += 1
        print(f"\r[tts] {done}/{n}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)

    with tempfile.NamedTemporaryFile(suffix=".raw") as raw:
        raw.write(pcm); raw.flush()
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1",
             "-i", raw.name,
             "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
             "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", a.bitrate,
             a.out], check=True)
    dur = len(pcm) / 2 / RATE
    print(f"[tts] wrote {a.out} ({dur:.1f}s)", file=sys.stderr)


if __name__ == "__main__":
    main()
