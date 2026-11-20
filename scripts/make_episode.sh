#!/usr/bin/env bash
# 台本と説明文からエピソードを作って feed.xml を更新する（git 操作はしない）。
#   bash scripts/make_episode.sh <回番号> "<タイトル>"
# 前提: transcripts/NNN.txt（台本）と transcripts/NNN.desc.txt（説明文）があること
set -euo pipefail
cd "$(dirname "$0")/.."
N="$1"; TITLE="$2"
NNN=$(printf '%03d' "$N")
bash scripts/setup_voicevox.sh
OUT="$(mktemp -d)/ep.mp3"
python3 scripts/tts.py "transcripts/$NNN.txt" "$OUT"
python3 scripts/publish.py add --mp3 "$OUT" --title "$TITLE" \
  --description-file "transcripts/$NNN.desc.txt" --number "$N"
python3 -c "import xml.dom.minidom as m; m.parse('feed.xml'); print('[make_episode] feed.xml OK')"
