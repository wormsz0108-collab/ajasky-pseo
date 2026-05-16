"""기존 글의 og_image_url을 composed branded JPG로 일괄 재합성.

흐름:
  1) Worker GET /api/posts/list?missing_og=1 으로 raw photo 가리키는 글 목록
  2) 각 글에 대해:
       - 원본 사진을 HTTPS public (Worker /media/*) 으로 fetch
       - compose_og 로 분홍 리본 + 노랑 강조 + 검정 브랜드바 박힌 JPG 합성
       - R2 에 og/{slug}.jpg 로 업로드
       - Worker PATCH /api/posts/{id}/og 로 URL 갱신
  3) 다음 페이지로

실행:
  python content-pipeline/backfill_og.py            # 전부
  python content-pipeline/backfill_og.py --limit 5  # 5건만 (테스트)

필요 환경변수:
  WORKER_API_TOKEN, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

# content-pipeline 가 같은 디렉터리에 있다고 가정
sys.path.insert(0, str(Path(__file__).parent))

from og_compose import compose_og
from run_once import _split_board

SITE = os.environ.get("SITE_DOMAIN", "ajasky.co.kr")
BASE = f"https://{SITE}"


def _auth() -> dict[str, str]:
    token = os.environ.get("WORKER_API_TOKEN")
    if not token:
        # 로컬 fallback: .secrets/worker_api_token.txt
        secret_file = Path(__file__).parent.parent / ".secrets" / "worker_api_token.txt"
        if secret_file.exists():
            token = secret_file.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("WORKER_API_TOKEN env var or .secrets/worker_api_token.txt required")
    return {"Authorization": f"Bearer {token}"}


def list_missing(offset: int, limit: int) -> list[dict]:
    r = requests.get(
        f"{BASE}/api/posts/list",
        params={"missing_og": "1", "limit": limit, "offset": offset},
        headers=_auth(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["posts"]


def fetch_source(photo_url: str) -> bytes:
    r = requests.get(f"{BASE}{photo_url}", timeout=30)
    r.raise_for_status()
    return r.content


def patch_og(post_id: int, url: str) -> None:
    r = requests.patch(
        f"{BASE}/api/posts/{post_id}/og",
        json={"og_image_url": url},
        headers={**_auth(), "Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()


def backfill_one(post: dict) -> bool:
    pid = post["id"]
    slug = post["slug"]
    region = post["region"]
    board_title = post["board_title"]
    photo_url = post["og_image_url"]

    if not photo_url or not photo_url.startswith("/media/"):
        print(f"  [skip] id={pid}: no photo url ({photo_url!r})")
        return False

    try:
        src = fetch_source(photo_url)
    except Exception as e:
        print(f"  [fail] id={pid}: fetch source failed: {e}", file=sys.stderr)
        return False

    try:
        ribbon, head_main = _split_board(board_title)
        composed = compose_og(
            src, ribbon=ribbon, headline_prefix=region, headline_main=head_main,
        )
    except Exception as e:
        print(f"  [fail] id={pid}: compose failed: {e}", file=sys.stderr)
        return False

    try:
        r = requests.post(
            f"{BASE}/api/og-upload",
            params={"slug": slug},
            data=composed,
            headers={**_auth(), "Content-Type": "image/jpeg"},
            timeout=30,
        )
        r.raise_for_status()
        new_url = r.json()["url"]
    except Exception as e:
        print(f"  [fail] id={pid}: og-upload failed: {e}", file=sys.stderr)
        return False

    try:
        patch_og(pid, new_url)
    except Exception as e:
        print(f"  [fail] id={pid}: PATCH failed: {e}", file=sys.stderr)
        return False

    print(f"  [ok] id={pid} slug={slug!r} → {new_url}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="max total posts to process")
    ap.add_argument("--page-size", type=int, default=20, help="per-page list size")
    ap.add_argument("--sleep", type=float, default=0.5, help="seconds between posts")
    args = ap.parse_args()

    processed = 0
    success = 0
    offset = 0
    while True:
        page = list_missing(offset=offset, limit=args.page_size)
        if not page:
            break
        print(f"[page] offset={offset} got {len(page)} posts")
        for post in page:
            if args.limit is not None and processed >= args.limit:
                break
            if backfill_one(post):
                success += 1
            processed += 1
            time.sleep(args.sleep)
        if args.limit is not None and processed >= args.limit:
            break
        # 모든 페이지 처리 후 offset은 0 유지 — patch 후 그 글들이 missing_og=1 결과에서 빠지므로
        # 다음 호출에 자동으로 새 페이지가 잡힘. offset 증가는 같은 글 반복 회피용 보조.
        if len(page) < args.page_size:
            break

    print(f"[done] processed={processed} success={success}")


if __name__ == "__main__":
    main()
