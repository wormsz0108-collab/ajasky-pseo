"""하루치 1건 발행 사이클.

흐름:
  1. (region, board, longtail) 랜덤 선택
  2. Gemini로 9-섹션 글 생성
  3. Worker /api/posts 로 POST
  4. 결과 출력

GitHub Actions가 이걸 cron으로 매일 호출.
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from generate import generate_post
from image_pool import pick_photo_key
from longtails import get_longtails, LONGTAILS_BY_BOARD
from og_compose import compose_og
from publish import publish, slugify_ko
from r2_client import get_object, put_object
from regions import all_region_targets


def _split_board(board_title: str) -> tuple[str, str]:
    """보드 → (ribbon, headline_main). thumbnail-text.ts 와 동일 로직."""
    parts = board_title.split()
    if len(parts) == 2:
        return parts[1], parts[0]
    # 접미사 분리
    for suffix in ("차량", "작업차", "이용료", "작업"):
        if board_title.endswith(suffix) and len(board_title) - len(suffix) >= 2:
            return suffix, board_title[: -len(suffix)]
    return "", board_title


SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "ajasky.co.kr")

# 8개 보드 (slug, title) — DB seed.sql 와 동기 유지
BOARDS = [
    ("스카이차",         "스카이차"),
    ("스카이차-일대",     "스카이차 일대"),
    ("스카이-작업차",     "스카이 작업차"),
    ("스카이차-요금",     "스카이차 요금"),
    ("스카이차-비용",     "스카이차 비용"),
    ("스카이차-가격",     "스카이차 가격"),
    ("스카이차-이용료",   "스카이차 이용료"),
    ("고소작업차량",      "고소작업차량"),
]


def pick_target():
    region, region_type = random.choice(all_region_targets())
    board_slug, board_title = random.choice(BOARDS)
    longtail = random.choice(get_longtails(board_title))
    return region, region_type, board_slug, board_title, longtail


def build_og(slug: str, region: str, board_title: str) -> str:
    """OG 이미지 URL 결정.

    우선순위:
      1) R2 키가 있으면 → 사진 합성(텍스트 오버레이) → R2에 업로드 → 그 URL
      2) R2 합성 실패해도 → pick_photo_key 결과 (Worker가 직접 R2에서 서빙)
      3) 그것도 실패하면 → /media/hero.jpg 최후 fallback

    글 slug 결정적 → 같은 slug 재시도해도 같은 사진.
    """
    photo_key = pick_photo_key(slug)
    fallback_url = f"/media/{photo_key}"   # Worker가 R2에서 직접 서빙 — R2 키 불필요

    # R2 키 없거나 쓰기 권한 없으면 합성 스킵 — fallback URL로 충분
    if not os.environ.get("R2_ACCESS_KEY_ID"):
        return fallback_url

    try:
        source_bytes = get_object(photo_key)
        ribbon, head_main = _split_board(board_title)
        composed = compose_og(
            source_bytes,
            ribbon=ribbon or region,
            headline_prefix=region if ribbon else "",
            headline_main=head_main,
        )
        og_key = f"og/{slug}.jpg"
        put_object(og_key, composed, "image/jpeg")
        return f"/media/{og_key}"
    except Exception as e:
        print(f"[warn] OG compose failed, using raw photo: {e}", file=sys.stderr)
        return fallback_url


def build_payload(region: str, region_type: str, board_slug: str, board_title: str, longtail: str, generated: dict) -> dict:
    title = generated["title"]
    slug = slugify_ko(f"{region}-{board_title}-{longtail}")[:280]
    og_url = build_og(slug, region, board_title)

    return {
        "site_domain": SITE_DOMAIN,
        "board_slug": board_slug,
        "slug": slug,
        "title": title,
        "region": region,
        "region_type": region_type,
        "meta_description": generated["meta_description"],
        "meta_keywords": generated["meta_keywords"],
        "body_md": generated["body_md"],
        "toc_json": json.dumps(generated.get("toc", []), ensure_ascii=False),
        "faq_json": json.dumps(generated.get("faq", []), ensure_ascii=False),
        "og_image_url": og_url,
    }


def main():
    print(f"[run_once] start {datetime.now(timezone.utc).isoformat()}")

    # 매 cron 트리거마다 일정 확률로 스킵 → 하루 13~20개 변동 폭 확보
    # 20 트리거/일 × p(0.825) ≈ 평균 16.5 (이론적으로 13~20 95% 범위)
    p = float(os.environ.get("PUBLISH_PROBABILITY", "0.825"))
    if random.random() > p:
        print(f"[skip] random skip (probability={p})")
        return

    region, region_type, board_slug, board_title, longtail = pick_target()
    print(f"[target] region={region!r} board={board_title!r} longtail={longtail!r}")

    try:
        generated = generate_post(region, board_title, longtail)
    except Exception as e:
        print(f"[error] generate failed: {e}", file=sys.stderr)
        sys.exit(1)

    payload = build_payload(region, region_type, board_slug, board_title, longtail, generated)
    print(f"[generated] title={payload['title']!r}")
    print(f"[generated] slug={payload['slug']!r}")

    try:
        result = publish(payload)
    except Exception as e:
        print(f"[error] publish failed: {e}", file=sys.stderr)
        sys.exit(2)

    if result is None:
        print("[result] duplicate — skipped (will pick different target next run)")
    else:
        print(f"[result] published id={result.get('id')} url={result.get('url')}")


if __name__ == "__main__":
    main()
