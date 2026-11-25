# 音楽の発掘FM

毎朝ひとつ、あなたのためだけにアルバムを発掘する、パーソナル音声ポッドキャスト。

- Podcast フィード: https://yuukitakuwan-cpu.github.io/music-fm/feed.xml
- Web ページ: https://yuukitakuwan-cpu.github.io/music-fm/
- 音声: VOICEVOX:No.7（第6回まではVOICEVOX:春日部つむぎ）

## 構成
| パス | 内容 |
|---|---|
| `scripts/setup_voicevox.sh` | VOICEVOX（voicevox_core 0.17 内蔵の公式エンジン CPU 版）を取得・起動。冪等なので毎セッション実行してOK |
| `scripts/tts.py` | 台本テキスト → mp3（声の設定は podcast.json の voice、ffmpeg で整音・ラウドネス正規化） |
| `scripts/publish.py` | mp3 を `episodes/` に追加し `feed.xml`（iTunes 対応 RSS）と `index.html` を再生成。直近30回だけ保持 |
| `scripts/apple_music_check.py` | Apple Music（日本）での配信・ストリーミング可否を確認してリンクを出す |
| `scripts/make_episode.sh` | 上記をまとめて1回分を作る |
| `scripts/make_artwork.py` | 番組アートワーク `artwork.png`（3000×3000）を生成 |
| `transcripts/` | 各回の台本と説明文 |
| `history.md` | 紹介済みアルバム（重複防止） |
| `ROUTINE.md` | 毎朝のスケジュールタスクの手順 |

`feed.xml` には `<itunes:block>Yes</itunes:block>` を入れてあり、Apple Podcasts のディレクトリには載りません（URL で個人登録して聴く用）。

## クレジット
- 音声合成: VOICEVOX:No.7（第6回まではVOICEVOX:春日部つむぎ）（https://voicevox.hiroshiba.jp/ ）
- 紹介する楽曲・アルバムの権利は各権利者に帰属します。歌詞の引用は行いません。
