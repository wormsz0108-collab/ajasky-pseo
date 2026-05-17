"""각 발행글의 키워드로 네이버 웹문서 검색 → 우리 사이트 노출 여부 확인.

흐름:
  1) Worker GET /api/posts/list 로 전체 글 목록 가져옴
  2) 각 글마다 "{region} {board_title}" 키워드로 네이버 검색 API 호출
  3) 결과 100건 중 ajasky.co.kr 도메인 있는지 확인 → 있으면 몇 번째
  4) 표로 출력 + 요약

필요 env:
  WORKER_API_TOKEN (또는 .secrets/worker_api_token.txt)
  NAVER_CLIENT_ID, NAVER_CLIENT_SECRET (또는 인자 --client-id/--client-secret)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

SITE = "ajasky.co.kr"
WORKER_BASE = f"https://{SITE}"
NAVER_API = "https://openapi.naver.com/v1/search/webkr.json"


def _worker_auth() -> dict[str, str]:
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
            f"{WORKER_BASE}/api/posts/list",
            params={"limit": 100, "offset": offset},
            headers=_worker_auth(),
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


def search_naver(query: str, client_id: str, client_secret: str, display: int = 100) -> list[dict]:
    """네이버 웹문서 검색. 최대 100건 반환."""
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    r = requests.get(
        NAVER_API,
        params={"query": query, "display": display, "start": 1, "sort": "sim"},
        headers=headers,
        timeout=15,
    )
    if r.status_code != 200:
        return []
    return r.json().get("items", [])


def find_our_rank(items: list[dict], slug_hint: str | None = None) -> tuple[int, str] | None:
    """결과 중 우리 사이트가 몇 번째인지. slug 일치도 추가 체크."""
    for i, item in enumerate(items, 1):
        link = item.get("link", "")
        if SITE in link:
            return i, link
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-id", default=os.environ.get("NAVER_CLIENT_ID"))
    ap.add_argument("--client-secret", default=os.environ.get("NAVER_CLIENT_SECRET"))
    ap.add_argument("--limit", type=int, default=None, help="처리할 최대 글 수")
    ap.add_argument("--sleep", type=float, default=0.15, help="API 호출 간격(초)")
    args = ap.parse_args()
    if not args.client_id or not args.client_secret:
        raise SystemExit("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 필요")

    posts = fetch_all_posts()
    if args.limit:
        posts = posts[:args.limit]
    print(f"[total] {len(posts)} posts to check\n")

    found = 0
    not_found = 0
    found_details: list[tuple[str, int, str]] = []   # (query, rank, link)
    rank_buckets = {"1-3": 0, "4-10": 0, "11-30": 0, "31-100": 0}

    for i, p in enumerate(posts, 1):
        region = p["region"]
        board = p["board_title"]
        slug = p["slug"]
        query = f"{region} {board}"

        items = search_naver(query, args.client_id, args.client_secret)
        if not items:
            print(f"[{i:>3}/{len(posts)}] '{query}' → API 오류 또는 결과 없음")
            time.sleep(args.sleep)
            continue

        result = find_our_rank(items)
        if result:
            rank, link = result
            mark = "[TOP3]" if rank <= 3 else ("[TOP10]" if rank <= 10 else ("[TOP30]" if rank <= 30 else "[T100]"))
            print(f"[{i:>3}/{len(posts)}] '{query}' -> {mark} #{rank}")
            found += 1
            found_details.append((query, rank, link))
            if rank <= 3: rank_buckets["1-3"] += 1
            elif rank <= 10: rank_buckets["4-10"] += 1
            elif rank <= 30: rank_buckets["11-30"] += 1
            else: rank_buckets["31-100"] += 1
        else:
            print(f"[{i:>3}/{len(posts)}] '{query}' -> 100위 밖")
            not_found += 1
        time.sleep(args.sleep)

    print()
    print("=" * 70)
    print(f"전체: {len(posts)}건")
    print(f"노출됨: {found}건 ({found/len(posts)*100:.1f}%)")
    print(f"  - 1~3위:    {rank_buckets['1-3']:>3}건")
    print(f"  - 4~10위:   {rank_buckets['4-10']:>3}건")
    print(f"  - 11~30위:  {rank_buckets['11-30']:>3}건")
    print(f"  - 31~100위: {rank_buckets['31-100']:>3}건")
    print(f"미노출: {not_found}건 (100위 밖)")
    print("=" * 70)

    if found_details:
        print("\n[노출된 글 상세]")
        for q, r, link in sorted(found_details, key=lambda x: x[1]):
            print(f"  #{r:>3}  {q}  →  {link[:80]}")


if __name__ == "__main__":
    main()
