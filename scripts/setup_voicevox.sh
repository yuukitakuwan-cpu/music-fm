#!/usr/bin/env bash
# VOICEVOX (voicevox_core 内蔵の公式エンジン) を取得して localhost:50021 で起動する。
# 冪等：取得済みならダウンロードを飛ばし、起動済みなら何もしない。毎セッション実行してOK。
#
# 取得元: Docker Hub の公式イメージ voicevox/voicevox_engine (CPU版)
#   GitHub Releases が使えない環境でも、パッケージレジストリ経由で取得できるようにしている。
#   中身は libvoicevox_core.so (voicevox_core 0.17) + ONNX Runtime + 音声モデル(VVM) + OpenJTalk辞書。
#   Docker デーモンは不要（レジストリAPIから該当レイヤーだけを取り出して展開する）。
set -euo pipefail

IMAGE="voicevox/voicevox_engine"
TAG="${VOICEVOX_TAG:-cpu-ubuntu22.04-0.26.2}"
INSTALL_DIR="${VOICEVOX_DIR:-$HOME/.cache/voicevox}"
ENGINE_DIR="$INSTALL_DIR/opt/voicevox_engine"
PORT="${VOICEVOX_PORT:-50021}"
# 使うモデルだけ残す（0=春日部つむぎ等, 1=冥鳴ひまり, 6=No.7, 8=WhiteCUL, 24=夜語トバリ等）
KEEP_MODELS="${VOICEVOX_KEEP_MODELS:-0.vvm 1.vvm 6.vvm 8.vvm 24.vvm}"

need() { command -v "$1" >/dev/null 2>&1; }

# --- ffmpeg ---
if ! need ffmpeg; then
  echo "[setup] installing ffmpeg"
  if need apt-get; then
    (apt-get update -qq && apt-get install -y -qq ffmpeg) || sudo sh -c 'apt-get update -qq && apt-get install -y -qq ffmpeg'
  else
    echo "ffmpeg が見つかりません。手動でインストールしてください" >&2; exit 1
  fi
fi

engine_up() { curl -s --noproxy '*' -m 2 "http://127.0.0.1:$PORT/version" >/dev/null 2>&1; }

if engine_up; then
  echo "[setup] VOICEVOX engine already running on :$PORT"
  exit 0
fi

# --- download engine (once) ---
missing=0; for k in $KEEP_MODELS; do [ -f "$ENGINE_DIR/model/$k" ] || missing=1; done
if [ ! -x "$ENGINE_DIR/run" ] || [ $missing = 1 ]; then
  echo "[setup] downloading $IMAGE:$TAG (about 2GB, ~1-2 min)"
  mkdir -p "$INSTALL_DIR"
  arch="$(uname -m)"; case "$arch" in x86_64) plat=amd64;; aarch64|arm64) plat=arm64;; *) echo "unsupported arch $arch" >&2; exit 1;; esac
  token=$(curl -fsS "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$IMAGE:pull" \
          | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
  reg="https://registry-1.docker.io/v2/$IMAGE"
  acc='application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'
  index=$(curl -fsS -H "Authorization: Bearer $token" -H "Accept: $acc" "$reg/manifests/$TAG")
  digest=$(printf '%s' "$index" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for m in d.get('manifests',[]):
    if m.get('platform',{}).get('architecture')=='$plat': print(m['digest']); break")
  manifest=$(curl -fsS -H "Authorization: Bearer $token" -H "Accept: $acc" "$reg/manifests/$digest")
  # エンジン本体は最大のレイヤー（COPY /opt/voicevox_engine）
  layer=$(printf '%s' "$manifest" | python3 -c '
import json,sys
d=json.load(sys.stdin); print(max(d["layers"], key=lambda l:l["size"])["digest"])')
  tmp="$INSTALL_DIR/.partial"; rm -rf "$tmp"; mkdir -p "$tmp"
  curl -fsSL --retry 4 -H "Authorization: Bearer $token" "$reg/blobs/$layer" \
    | tar -xz -C "$tmp" --wildcards 'opt/voicevox_engine/*'
  # 不要なモデルを削除してディスク節約
  for f in "$tmp"/opt/voicevox_engine/model/*.vvm; do
    keep=0; for k in $KEEP_MODELS; do [ "$(basename "$f")" = "$k" ] && keep=1; done
    [ $keep = 1 ] || rm -f "$f"
  done
  rm -rf "$INSTALL_DIR/opt"; mv "$tmp/opt" "$INSTALL_DIR/opt"; rm -rf "$tmp"
  echo "[setup] installed to $ENGINE_DIR"
fi

# --- start engine ---
echo "[setup] starting VOICEVOX engine on 127.0.0.1:$PORT"
# exec で subshell を置き換え、標準入出力をすべてログへ（呼び出し元のパイプを掴まないように）
( cd "$ENGINE_DIR" && exec setsid nohup ./run --host 127.0.0.1 --port "$PORT" \
    > "$INSTALL_DIR/engine.log" 2>&1 < /dev/null ) > /dev/null 2>&1 < /dev/null &
disown || true
for i in $(seq 1 90); do
  if engine_up; then echo "[setup] engine ready ($(curl -s --noproxy '*' "http://127.0.0.1:$PORT/version"))"; exit 0; fi
  sleep 2
done
echo "[setup] engine failed to start; log:" >&2; tail -30 "$INSTALL_DIR/engine.log" >&2; exit 1
