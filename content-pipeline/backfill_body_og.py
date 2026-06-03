"""본문 i=1, i=3, i=5 위치용 브랜디드 OG 변형 3장 일괄 생성.

각 글마다:
  - body1 = bodyPhotos[0] 사진 + 동일 hero 텍스트 오버레이 (compose_og)
  - body2 = bodyPhotos[1] 사진 + 동일 오버레이
  - body3 = bodyPhotos[2] 사진 + 동일 오버레이

R2 키: og/body1-{slug}.jpg, og/body2-{slug}.jpg, og/body3-{slug}.jpg

이미지 4장(hero + body 3장) 모두 같은 디자인이지만 배경 사진 다름.
→ 네이버 이미지 검색 노출 확대, 스팸 회피.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from og_compose import compose_for_site
from run_once import _split_board

SITE = os.environ.get("SITE_DOMAIN", "ajasky.co.kr")
BASE = f"https://{SITE}"
POOL_SIZE = 121   # photos/001~121.jpg


def _auth() -> dict[str, str]:
    token = os.environ.get("WORKER_API_TOKEN")
    if not token:
        secret_file = Path(__file__).parent.parent / ".secrets" / "worker_api_token.txt"
        if secret_file.exists():
            token = secret_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("WORKER_API_TOKEN required")
    return {"Authorization": f"Bearer {token}"}


def _djb2(s: str) -> int:
    """src/lib/body-photos.ts 의 hash 함수와 동일 (djb2)."""
    h = 5381
    for c in s.encode("utf-8"):
        h = ((h << 5) + h + c) & 0xFFFFFFFF
    return h


def _hero_photo_n(slug: str) -> int:
    """image_pool.pick_photo_key 와 동일 로직 (hero 사진 번호)."""
    h = hashlib.sha256(slug.encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") % POOL_SIZE + 1


def body_photo_keys(slug: str) -> list[str]:
    """한 글 안에서 hero + body1/2/3 = 4장이 전부 다른 photo 가 되도록 회피.

    djb2 해시로 후보 생성 → 이미 쓴 번호면 다음 시도(seed 증가). 121장 풀에 4장만
    뽑으면 되니 재시도 거의 없음. 다른 slug 도 hero+body 회피 적용해 전체적으로
    중복 감소.
    """
    used: set[int] = {_hero_photo_n(slug)}
    keys: list[str] = []
    i = 0
    while len(keys) < 3 and i < POOL_SIZE * 2:    # safety bound
        n = (_djb2(f"{slug}#body{i}") % POOL_SIZE) + 1
        if n not in used:
            used.add(n)
            keys.append(f"photos/{n:03d}.jpg")
        i += 1
    return keys


def fetch_source(photo_key: str) -> bytes:
    r = requests.get(f"{BASE}/media/{photo_key}", timeout=30)
    r.raise_for_status()
    return r.content


def upload_variant(slug: str, variant: str, jpg_bytes: bytes) -> str:
    r = requests.post(
        f"{BASE}/api/og-upload",
        params={"slug": slug, "variant": variant},
        data=jpg_bytes,
        headers={**_auth(), "Content-Type": "image/jpeg"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["url"]


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


def backfill_one(post: dict) -> int:
    pid = post["id"]
    slug = post["slug"]
    region = post["region"]
    board = post["board_title"]
    ribbon, head_main = _split_board(board)

    photo_keys = body_photo_keys(slug)
    success = 0
    for i, photo_key in enumerate(photo_keys, 1):
        variant = f"body{i}"
        try:
            src = fetch_source(photo_key)
            composed = compose_for_site(
                SITE, src, ribbon=ribbon, headline_prefix=region, headline_main=head_main,
            )
            upload_variant(slug, variant, composed)
            success += 1
        except Exception as e:
            print(f"  [fail] id={pid} {variant}: {e}", file=sys.stderr)
    return success


def main():
    posts = fetch_all_posts()
    print(f"[total] {len(posts)} posts × 3 body variants = {len(posts)*3} files")
    total_success = 0
    for i, p in enumerate(posts, 1):
        n = backfill_one(p)
        total_success += n
        print(f"[{i:>3}/{len(posts)}] id={p['id']} [{p['region']}] [{p['board_title']}] -> {n}/3 변형")
        time.sleep(0.2)
    print(f"\n[done] {total_success}/{len(posts)*3} files uploaded")


if __name__ == "__main__":
    main()
