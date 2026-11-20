#!/usr/bin/env python3
"""エピソードを追加して feed.xml（iTunes 対応 RSS）と index.html を再生成する。

使い方:
    python3 scripts/publish.py add --mp3 out.mp3 --title "..." --description-file desc.txt \
        [--date 2026-11-21] [--number N]
    python3 scripts/publish.py build      # episodes.json から feed.xml / index.html を作り直すだけ

- mp3 は episodes/ にコピーされる（ファイル名: YYYYMMDD-NNN.mp3）
- 直近 keep_episodes 回（既定30）だけ残し、古い mp3 は削除する
- 説明文の末尾には VOICEVOX のクレジットを必ず付ける（無ければ自動追記）
- 説明文中の URL は HTML 版（content:encoded）でリンクになる
"""
import argparse
import datetime as dt
import email.utils
import html
import json
import os
import re
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = json.load(open(os.path.join(ROOT, "podcast.json"), encoding="utf-8"))
DB = os.path.join(ROOT, "episodes.json")
EPDIR = os.path.join(ROOT, "episodes")
JST = dt.timezone(dt.timedelta(hours=9))


def load():
    if os.path.exists(DB):
        return json.load(open(DB, encoding="utf-8"))
    return []


def save(eps):
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(eps, f, ensure_ascii=False, indent=2)
        f.write("\n")


def duration_sec(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return int(round(float(out.stdout.strip())))


def hms(s):
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def credit_ok(desc):
    return CONF["voice_credit"] in desc


def to_html(text):
    parts = []
    for para in re.split(r"\n\s*\n", text.strip()):
        p = html.escape(para)
        p = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', p)
        parts.append("<p>" + p.replace("\n", "<br>") + "</p>")
    return "".join(parts)


def cdata(s):
    return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def build(eps):
    base = CONF["base_url"].rstrip("/")
    art = f"{base}/{CONF['artwork']}"
    now = email.utils.format_datetime(dt.datetime.now(JST))
    items = []
    for e in sorted(eps, key=lambda e: e["pub_date"], reverse=True):
        url = f"{base}/episodes/{e['file']}"
        pub = email.utils.format_datetime(dt.datetime.fromisoformat(e["pub_date"]))
        items.append(f"""    <item>
      <title>{escape(e['title'])}</title>
      <itunes:title>{escape(e['title'])}</itunes:title>
      <itunes:episode>{e['number']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <description>{cdata(e['description'])}</description>
      <content:encoded>{cdata(to_html(e['description']))}</content:encoded>
      <itunes:summary>{cdata(e['description'])}</itunes:summary>
      <enclosure url="{escape(url)}" length="{e['bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(e['guid'])}</guid>
      <pubDate>{pub}</pubDate>
      <itunes:duration>{hms(e['duration'])}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:image href="{escape(art)}"/>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(CONF['title'])}</title>
    <link>{escape(base)}/</link>
    <atom:link href="{escape(base)}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>{CONF['language']}</language>
    <description>{cdata(CONF['description'])}</description>
    <itunes:subtitle>{escape(CONF['subtitle'])}</itunes:subtitle>
    <itunes:summary>{cdata(CONF['description'])}</itunes:summary>
    <itunes:author>{escape(CONF['author'])}</itunes:author>
    <itunes:owner><itunes:name>{escape(CONF['owner_name'])}</itunes:name></itunes:owner>
    <itunes:image href="{escape(art)}"/>
    <image><url>{escape(art)}</url><title>{escape(CONF['title'])}</title><link>{escape(base)}/</link></image>
    <itunes:category text="{escape(CONF['category'])}"><itunes:category text="{escape(CONF['subcategory'])}"/></itunes:category>
    <itunes:explicit>{'true' if CONF['explicit'] else 'false'}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <itunes:block>Yes</itunes:block>
    <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    with open(os.path.join(ROOT, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(feed)

    rows = "\n".join(
        f'<li><b>{html.escape(e["title"])}</b> <small>{e["pub_date"][:10]}</small><br>'
        f'<audio controls preload="none" src="episodes/{e["file"]}"></audio>'
        f'<div class="d">{to_html(e["description"])}</div></li>'
        for e in sorted(eps, key=lambda e: e["pub_date"], reverse=True))
    page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(CONF['title'])}</title>
<link rel="alternate" type="application/rss+xml" href="feed.xml">
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:0 auto;padding:16px;background:#111;color:#eee}}
a{{color:#ffb86b}}img{{width:160px;border-radius:12px}}li{{margin:0 0 28px;list-style:none}}ul{{padding:0}}
audio{{width:100%;margin:8px 0}}.d{{font-size:14px;color:#bbb}}</style></head><body>
<img src="{CONF['artwork']}" alt="">
<h1>{html.escape(CONF['title'])}</h1>
<p>{html.escape(CONF['subtitle'])}</p>
<p>Podcastアプリに登録するURL: <a href="feed.xml">{html.escape(base)}/feed.xml</a></p>
<ul>
{rows}
</ul></body></html>
"""
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)


def prune(eps):
    keep = CONF["keep_episodes"]
    eps = sorted(eps, key=lambda e: e["pub_date"], reverse=True)
    for e in eps[keep:]:
        p = os.path.join(EPDIR, e["file"])
        if os.path.exists(p):
            os.remove(p)
            print(f"[publish] pruned {e['file']}", file=sys.stderr)
    return eps[:keep]


def add(a):
    eps = load()
    desc = open(a.description_file, encoding="utf-8").read().strip()
    if not credit_ok(desc):
        desc += f"\n\n音声：{CONF['voice_credit']}"
    date = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(JST).date()
    number = a.number if a.number is not None else (max([e["number"] for e in eps], default=-1) + 1)
    fname = f"{date.strftime('%Y%m%d')}-{number:03d}.mp3"
    os.makedirs(EPDIR, exist_ok=True)
    dst = os.path.join(EPDIR, fname)
    shutil.copyfile(a.mp3, dst)
    pub = dt.datetime.now(JST).replace(microsecond=0)
    if a.date and pub.date() != date:
        pub = dt.datetime.combine(date, dt.time(6, 52), JST)
    eps = [e for e in eps if e["number"] != number]
    eps.append(dict(number=number, title=a.title, description=desc, file=fname,
                    bytes=os.path.getsize(dst), duration=duration_sec(dst),
                    pub_date=pub.isoformat(), guid=f"music-fm-{number:04d}-{date.isoformat()}"))
    eps = prune(eps)
    save(eps)
    build(eps)
    print(f"[publish] added #{number}: {a.title} -> episodes/{fname}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("--mp3", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description-file", required=True)
    p.add_argument("--date")
    p.add_argument("--number", type=int)
    sub.add_parser("build")
    a = ap.parse_args()
    if a.cmd == "add":
        add(a)
    else:
        build(load())


if __name__ == "__main__":
    main()
