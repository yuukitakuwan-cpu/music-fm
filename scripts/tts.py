#!/usr/bin/env python3
"""台本テキストを VOICEVOX で女性ボイスの mp3 にする。

使い方:
    python3 scripts/tts.py script.txt out.mp3 [--speaker 8]

台本の書式:
    - 1行 = 1発話。空行 = 少し長めの間。
    - "#" で始まる行はコメント（読まない）。
    - "[jingle]" だけの行 = 短いチャイムを挟む（番組のコーナー区切り用）。

事前に scripts/setup_voicevox.sh でエンジンを起動しておくこと。
既定の声と読み上げ設定は podcast.json の "voice"（話者ID・速さ・抑揚・間・仕上げ・クレジット）。
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

RATE = 24000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 声の設定は podcast.json の "voice" に集約（話者・速さ・抑揚・間・クレジット）
VOICE = json.load(open(os.path.join(ROOT, "podcast.json"), encoding="utf-8")).get("voice", {})


def api(path, params=None, body=None):
    url = HOST + path + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else b""
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with _opener.open(req, timeout=300) as r:
        return r.read()


def synth_line(text, speaker, speed, pitch, intonation, pause_scale):
    q = json.loads(api("/audio_query", {"text": text, "speaker": speaker}))
    q.update(speedScale=speed, pitchScale=pitch, intonationScale=intonation,
             volumeScale=1.0, prePhonemeLength=0.05, postPhonemeLength=0.1,
             pauseLengthScale=pause_scale,
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
    ap.add_argument("--speaker", type=int, default=VOICE.get("speaker", 8))
    ap.add_argument("--speed", type=float, default=VOICE.get("speed", 1.12))
    ap.add_argument("--pitch", type=float, default=VOICE.get("pitch", 0.02))
    ap.add_argument("--intonation", type=float, default=VOICE.get("intonation", 1.25))
    ap.add_argument("--pause-scale", type=float, default=VOICE.get("pause_scale", 1.0))
    ap.add_argument("--line-gap", type=float, default=VOICE.get("line_gap", 0.18))
    ap.add_argument("--polish", type=int, default=VOICE.get("polish", 0),
                    help="1 = 軽いEQ・コンプ・ごく薄い残響でスタジオっぽく（機械っぽさを和らげる）")
    ap.add_argument("--bgm-volume", type=float, default=VOICE.get("bgm_volume", 0.0),
                    help="BGM（assets/bgm_loop.wav）の音量。0でBGMなし。声が出ている間は自動で下がる")
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
        pcm += read_pcm(synth_line(line, a.speaker, a.speed, a.pitch, a.intonation, a.pause_scale))
        # 行末の間を少し揺らして、一定リズムの機械っぽさを減らす
        gap = a.line_gap
        if line.endswith(("？", "?", "！", "!")):
            gap += 0.12
        elif line.endswith("。"):
            gap += 0.06
        pcm += silence(gap)
        done += 1
        print(f"\r[tts] {done}/{n}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)

    polish = ("highpass=f=80,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=1.5,"
              "deesser=i=0.3,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120,"
              "aecho=0.85:0.7:28|47:0.10|0.06,") if a.polish else ""
    voice_sec = len(pcm) / 2 / RATE
    bgm = os.path.join(ROOT, "assets", "bgm_loop.wav")
    use_bgm = a.bgm_volume > 0
    if use_bgm and not os.path.exists(bgm):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "make_bgm.py")], check=True)
    with tempfile.NamedTemporaryFile(suffix=".raw") as raw:
        raw.write(pcm); raw.flush()
        if use_bgm:
            lead, tail = 2.5, 4.0
            total = voice_sec + lead + tail
            fc = (f"[0:a]aresample=44100,{polish}adelay={int(lead*1000)}:all=1,"
                  f"apad=whole_dur={total:.2f},aformat=channel_layouts=stereo,asplit=2[v][sc];"
                  f"[1:a]volume={a.bgm_volume},atrim=0:{total:.2f},asetpts=N/SR/TB,"
                  f"afade=t=in:d=1.5,afade=t=out:st={total-3.5:.2f}:d=3.5[b];"
                  f"[b][sc]sidechaincompress=threshold=0.015:ratio=5:attack=30:release=600[bd];"
                  f"[v][bd]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[out]")
            cmd = ["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1",
                   "-i", raw.name, "-stream_loop", "-1", "-i", bgm,
                   "-filter_complex", fc, "-map", "[out]",
                   "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "128k", a.out]
        else:
            cmd = ["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1",
                   "-i", raw.name, "-af", polish + "loudnorm=I=-16:TP=-1.5:LRA=11",
                   "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", a.bitrate, a.out]
        subprocess.run(cmd, check=True)
    dur = len(pcm) / 2 / RATE
    print(f"[tts] wrote {a.out} ({dur:.1f}s)", file=sys.stderr)


if __name__ == "__main__":
    main()
