"""기존 글의 meta_keywords 를 derive_keywords 결과로 일괄 갱신.

사용자가 "관악구 스카이차" / "관악구스카이차" / "관악구 스카이" / "관악구스카이"
등 어떻게 검색해도 매칭되도록.

실행:
  python content-pipeline/backfill_keywords.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from keyword_variants import derive_keywords

SITE = os.environ.get("SITE_DOMAIN", "ajasky.co.kr")
BASE = f"https://{SITE}"


def _auth() -> dict[str, str]:
    token = os.environ.get("WORKER_API_TOKEN")
    if not token:
        secret_file = Path(__file__).parent.parent / ".secrets" / "worker_api_token.txt"
        if secret_file.exists():
            token = secret_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("WORKER_API_TOKEN required")
    return {"Authorization": f"Bearer {token}"}


def fetch_all_posts() -> list[dict]:
    posts: list[dict] = []
    offset = 0
    while True:
        r = requests.get(
            f"{BASE}/api/posts/list",
            params={"limit": 100, "offset": offset},
            headers=_auth(),
            timeout=30,
        )
        r.raise_for_status()
        page = r.json()["posts"]
        if not page:
            break
        posts.extend(page)
        if len(page) < 100:
            break
        offset += len(page)
    return posts


def main():
    posts = fetch_all_posts()
    print(f"[total] {len(posts)} posts")
    updated = 0
    unchanged = 0
    for i, p in enumerate(posts, 1):
        region = p["region"]
        board = p["board_title"]
        new_kw_list = derive_keywords(region, board)
        new_kw = ",".join(new_kw_list)
        old_kw = p.get("meta_keywords") or ""
        if old_kw == new_kw:
            unchanged += 1
            continue
        r = requests.patch(
            f"{BASE}/api/posts/{p['id']}/keywords",
            json={"meta_keywords": new_kw},
            headers={**_auth(), "Content-Type": "application/json"},
            timeout=30,
        )
        if r.status_code == 200:
            updated += 1
            print(f"[{i:>3}/{len(posts)}] id={p['id']} [{region}] [{board}] -> {len(new_kw_list)}개 키워드")
        else:
            print(f"[{i:>3}/{len(posts)}] id={p['id']} FAIL {r.status_code}: {r.text[:80]}", file=sys.stderr)
        time.sleep(0.1)
    print(f"\n[done] updated={updated}, unchanged={unchanged}, total={len(posts)}")


if __name__ == "__main__":
    main()
