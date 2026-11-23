#!/usr/bin/env python3
"""Apple Music（日本ストア）でアルバムが配信されているか確認し、リンクを出す。

使い方:
    python3 scripts/apple_music_check.py "アーティスト名" "アルバム名"
    python3 scripts/apple_music_check.py "アーティスト名"          # アルバム一覧を表示

iTunes Search API (country=jp) を使う。アルバム名を指定した場合は収録曲の isStreamable も確認し、
ストリーミング可能な曲があるものだけを Apple Music の URL 付きで出力して exit 0。
見つからなければ exit 1。
"""
import json
import sys
import time
import urllib.error
import unicodedata
import urllib.parse
import urllib.request


def norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    return "".join(ch for ch in s if ch.isalnum())


def fetch(url):
    """Apple のレート制限（403/429）に備えて少し待って再試行"""
    for i in range(5):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (403, 429, 503) or i == 4:
                raise
            time.sleep(5 * (i + 1))


def search(term, entity="album", limit=200):
    q = urllib.parse.urlencode({"term": term, "country": "JP", "entity": entity,
                                "limit": limit, "lang": "ja_jp"})
    return fetch(f"https://itunes.apple.com/search?{q}")["results"]


def streamable(collection_id):
    """アルバム収録曲のうち Apple Music でストリーミング可能な曲数 / 全曲数"""
    q = urllib.parse.urlencode({"id": collection_id, "entity": "song", "country": "JP"})
    songs = [x for x in fetch(f"https://itunes.apple.com/lookup?{q}")["results"]
             if x.get("wrapperType") == "track"]
    return sum(1 for x in songs if x.get("isStreamable")), len(songs)


def music_url(u):
    # itunes の collectionViewUrl を music.apple.com/jp の形に揃える
    u = u.split("?")[0].replace("itunes.apple.com", "music.apple.com")
    return u.replace("music.apple.com/us/", "music.apple.com/jp/")


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    artist = sys.argv[1]
    album = sys.argv[2] if len(sys.argv) > 2 else None
    res = search(f"{artist} {album}" if album else artist)
    if album:
        res += search(artist)
    na = norm(artist)
    hits, seen = [], set()
    for r in res:
        if r.get("wrapperType") != "collection" or r["collectionId"] in seen:
            continue
        seen.add(r["collectionId"])
        if na not in norm(r.get("artistName", "")) and norm(r.get("artistName", "")) not in na:
            continue
        if album and norm(album) not in norm(r["collectionName"]):
            continue
        hits.append(r)
    if album and not hits:
        # 日本ストアではアーティスト名がカタカナ表記のことがある（例: Astor Piazzolla → アストル・ピアソラ）。
        # その場合はアルバム名一致で拾い、表示されたアーティスト名を目視確認する。
        for r in res:
            if r.get("wrapperType") == "collection" and norm(album) in norm(r["collectionName"]) \
                    and r not in hits:
                hits.append(r)
    hits.sort(key=lambda r: r.get("releaseDate", ""))
    ok = []
    for r in hits:
        extra = ""
        if album:  # 個別確認時はストリーミング可否もチェック
            n_ok, n_all = streamable(r["collectionId"])
            extra = f" [streamable {n_ok}/{n_all}]"
            if n_ok == 0:
                continue
        ok.append(r)
        print(f'{r["artistName"]} / {r["collectionName"]} ({r.get("releaseDate","")[:10]}, '
              f'{r.get("trackCount","?")}曲){extra} {music_url(r["collectionViewUrl"])}')
    hits = ok
    if not hits:
        print("NOT FOUND on Apple Music (JP)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
