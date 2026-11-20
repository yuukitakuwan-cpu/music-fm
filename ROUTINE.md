# 毎朝の手順（スケジュールタスク用）

毎朝 6:52 (Asia/Tokyo) に実行。この手順どおりに 1 回分を作って main に push する。

## 0. 準備
```bash
cd music-fm   # リポジトリのルート
git checkout main && git pull origin main
bash scripts/setup_voicevox.sh   # 冪等。初回は約2分（2GB取得）、以降は即終了
```

## 1. アルバムを選ぶ
リスナーの好み（核は **哀愁のあるメロディックパンク**）:
Hi-STANDARD、ELLEGARDEN、10-FEET、HEY-SMITH、SiM、マキシマム ザ ホルモン、花冷え。、
サカナクション、Kroi、キタニタツヤ、羊文学、くるり、JUDY AND MARY、Green Day など。

- メジャーからマイナー（インディー、海外、昔の名盤、新譜）まで幅広く。7割くらいは哀愁メロコア/パンク寄り、
  残りは好みの周辺（オルタナ、ミクスチャー、ラウド、ギターロック、ファンク寄り等）から。
- **上に挙げた好きなアーティスト本人の作品より、「その好みならこれも刺さるはず」という発掘を優先**。
- `history.md` を読み、**同じアルバムは絶対に選ばない**。同じアーティストも直近20回は避ける。
- 除外: SHANK（`history.md` の除外リスト参照）。
- 候補が決まったら必ず Apple Music（日本）で配信を確認する:
  ```bash
  python3 scripts/apple_music_check.py "アーティスト名"            # アルバム一覧
  python3 scripts/apple_music_check.py "アーティスト名" "アルバム名" # 個別確認（streamable を確認）
  ```
  見つからない／streamable が 0 なら別の候補に変える。出力された `https://music.apple.com/jp/album/...` を使う。
- 曲名・リリース年などの事実は、`https://itunes.apple.com/lookup?id=<アルバムID>&entity=song&country=JP`
  や Web 検索で確認できたものだけを話す。不確かなことは言わない（言い切らない）。

## 2. 台本を書く → `transcripts/NNN.txt`（NNN = 3桁の回番号）
- 女性DJが**友達口調**で、リスナー「きみ」ひとりだけに話しかけるラジオ風。明るく元気に。
- 長さは約3分 = 本文 **900〜1100字** 程度（読み上げ速度 1.12 で ~2分40秒〜3分20秒）。
- 構成例: `[jingle]` → おはよう＋今日の天気や季節の一言（日付は JST）→ `[jingle]` → アルバム紹介
  （どんなバンドか／どんな音か／なぜきみに刺さるか／おすすめ曲を2曲くらい）→ `[jingle]` → 締め（説明欄にリンクあるよ、いってらっしゃい）。
- **歌詞は一切引用しない**（曲名を言うのはOK）。
- 書式: 1行=1発話、空行=間、`#`行はコメント、`[jingle]` でチャイム。
- 読み間違いしやすい英語のバンド名・曲名は**カタカナで**書く（例: ノーザン・ナインティーン）。
  数字も読ませたい形で書く（例: 二千十年、十一曲）。
- 読みの確認（任意）: `curl -s -X POST "http://127.0.0.1:50021/audio_query?speaker=8" --get --data-urlencode "text=..." | python3 -c "import json,sys;print(json.load(sys.stdin)['kana'])"`

## 3. 説明文を書く → `transcripts/NNN.desc.txt`
```
（1〜2行の紹介）

今日の一枚：アーティスト『アルバム』
Apple Music：https://music.apple.com/jp/album/...

（ひとこと／おすすめ曲）

音声：VOICEVOX:春日部つむぎ
```
- Apple Music のリンクは必須。VOICEVOX のクレジット `VOICEVOX:春日部つむぎ` も必須（無ければ publish.py が自動追記）。

## 4. 音声化してフィード更新
```bash
bash scripts/make_episode.sh <回番号> "第N回 アーティスト『アルバム』"
```
- episodes/ に mp3 を置き、feed.xml / index.html / episodes.json を更新、直近30回より古い mp3 は自動削除。

## 5. 履歴を追記して push
`history.md` の表に 1 行追記:
`| N | YYYY-MM-DD | アーティスト | アルバム | Apple Music URL |`

```bash
git add -A
git commit -m "第N回: アーティスト『アルバム』"
git push origin main   # 失敗したらネットワークエラーのみ最大4回リトライ
```
（作業ブランチ `claude/music-discovery-podcast-9pd50g` にも同じコミットを push してよい）

## 6. 確認
数分後に `https://yuukitakuwan-cpu.github.io/music-fm/feed.xml` に新しい回が載っていることを確認する。
