# 毎朝の手順（スケジュールタスク用）

毎朝 6:52 (Asia/Tokyo) に実行。この手順どおりに 1 回分を作って main に push する。

## 0. 準備
```bash
cd music-fm   # リポジトリのルート
git checkout main && git pull origin main
bash scripts/setup_voicevox.sh   # 冪等。初回は約2分（2GB取得）、以降は即終了
```

## 0.5 お便りを確認
`feedback.md` を読む。**未読のお便り**があれば台本の「お便りコーナー」で読み上げる（後述）。
「選曲メモ」は今日の選曲の最重要の手がかり。

## 1. アルバムを選ぶ
リスナーの好み（核は **哀愁のあるメロディックパンク**）:
Hi-STANDARD、ELLEGARDEN、10-FEET、HEY-SMITH、SiM、マキシマム ザ ホルモン、花冷え。、
サカナクション、Kroi、キタニタツヤ、羊文学、くるり、JUDY AND MARY、YUKI、MONKEY MAJIK、ORANGE RANGE、
Hump Back、DJ TATSUKI、Green Day など。SHANK「Set the fire」がめちゃくちゃ好み（SHANK 自体は紹介しない）。

- メジャーからマイナー（インディー、海外、昔の名盤、新譜）まで幅広く。7割くらいは哀愁メロコア/パンク寄り、
  残りは好みの周辺（オルタナ、ミクスチャー、ラウド、ギターロック、ファンク寄り等）から。
- **上に挙げた好きなアーティスト本人の作品より、「その好みならこれも刺さるはず」という発掘を優先**。
- `feedback.md` の選曲メモを反映して厳選する（刺さったポイントを持つ作品を優先し、いまいちだった方向は避ける）。
- **たまに（目安：5回に1回くらい）は突拍子もないジャンルを選んでよい**（ジャズ、民族音楽、アニソン、クラシック、
  ボサノヴァ、エレクトロ、昭和歌謡など）。その日は台本で「今日はちょっと冒険回！」と前置きし、
  きみの好み（疾走感・哀愁・ボーカルの熱さ・アルバムの物語性など）とどこでつながるかを語る。
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
- 長さは約3分 = 本文 **1150〜1300字** 程度（読み上げ速度 1.12 で約3分。900字だと2分半弱で短い）。
- 構成例: `[jingle]` → おはよう＋今日の天気や季節の一言（日付は JST）
  →（未読のお便りがあれば）**お便りコーナー**：「ラジオネーム、〇〇さん。」と名前を呼び、本文をそのまま読み上げ、
  DJとして感想にリアクションし、「その感想、今日の選曲に活かしたよ」と今日の一枚につなげる
  → `[jingle]` → アルバム紹介
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
読み上げたお便りは `feedback.md` で `状態：読了（第N回で紹介）` に変更する。
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
