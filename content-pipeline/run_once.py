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
import time
from datetime import datetime, timezone
from pathlib import Path

from generate import generate_post
from image_pool import pick_photo_key
from longtails import get_longtails, LONGTAILS_BY_BOARD
from og_compose import compose_og
from publish import publish, slugify_ko
from r2_client import get_object, put_object
from regions import all_region_targets

import requests as _requests


def _split_board(board_title: str) -> tuple[str, str]:
    """보드 → (ribbon, headline_main). thumbnail-text.ts BOARD_THUMBNAIL_MAP 과 동일."""
    BOARD_MAP = {
        "스카이차":      ("스카이차", "스카이차"),
        "스카이차 일대":  ("일대",    "스카이차"),
        "스카이 작업차":  ("작업차",  "스카이차"),
        "스카이차 요금":  ("요금",    "스카이차"),
        "스카이차 비용":  ("비용",    "스카이차"),
        "스카이차 가격":  ("가격",    "스카이차"),
        "스카이차 이용료": ("이용료",  "스카이차"),
        "고소작업차량":   ("차량",    "고소작업"),
    }
    return BOARD_MAP.get(board_title, (board_title, board_title))


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

    # 소스 사진 읽기 — R2 boto3 GetObject가 AccessDenied 나면 HTTPS public 으로 폴백.
    # (R2 API 토큰이 write-only 일 때 read는 어차피 막힘. Worker /media/* 가 public.)
    source_bytes: bytes | None = None
    try:
        source_bytes = get_object(photo_key)
    except Exception as e:
        print(f"[info] R2 GetObject failed, trying HTTPS public read: {e}", file=sys.stderr)
        try:
            import requests as _requests
            site = os.environ.get("SITE_DOMAIN", "ajasky.co.kr")
            r = _requests.get(f"https://{site}/media/{photo_key}", timeout=30)
            r.raise_for_status()
            source_bytes = r.content
        except Exception as e2:
            print(f"[warn] HTTPS source read also failed: {e2}", file=sys.stderr)
            return fallback_url

    try:
        ribbon, head_main = _split_board(board_title)
        composed = compose_og(
            source_bytes,
            ribbon=ribbon,             # 항상 보드 카테고리. 지역명 fallback 금지.
            headline_prefix=region,    # 큰 글자 1줄 = 지역
            headline_main=head_main,   # 큰 글자 2줄 = 메인 키워드
        )
    except Exception as e:
        print(f"[warn] OG compose failed: {e}", file=sys.stderr)
        return fallback_url

    # 업로드: R2 boto3 PutObject 가 AccessDenied 라서 Worker /api/og-upload 경유.
    # Worker는 MEDIA binding 으로 R2 full 권한이라 가능.
    try:
        token = os.environ.get("WORKER_API_TOKEN")
        if not token:
            print("[warn] WORKER_API_TOKEN missing, og upload skipped", file=sys.stderr)
            return fallback_url
        site = os.environ.get("SITE_DOMAIN", "ajasky.co.kr")
        r = _requests.post(
            f"https://{site}/api/og-upload",
            params={"slug": slug},
            data=composed,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "image/jpeg",
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["url"]
    except Exception as e:
        print(f"[warn] og upload via worker failed: {e}", file=sys.stderr)
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


def publish_one(idx: int = 0, max_retries: int = 5) -> bool:
    """1건 실제 발행될 때까지 최대 N회 재시도.

    중복(409) 발생 시 다른 (region, board, longtail) 조합으로 재시도.
    Gemini 생성 전에 slug 만 먼저 만들어 DB에 있는지 확인 → 있으면 Gemini 호출 자체 스킵해 비용 절약.
    """
    for attempt in range(max_retries):
        region, region_type, board_slug, board_title, longtail = pick_target()
        slug_preview = slugify_ko(f"{region}-{board_title}-{longtail}")[:280]
        print(f"[#{idx}.{attempt+1}] target region={region!r} board={board_title!r} slug={slug_preview!r}")

        # 사전 중복 체크: 같은 slug 글이 이미 발행됐는지 HEAD 로 확인.
        if _slug_exists(board_slug, slug_preview):
            print(f"[#{idx}.{attempt+1}] slug already exists, retry with different combo")
            continue

        try:
            generated = generate_post(region, board_title, longtail)
        except Exception as e:
            print(f"[#{idx}.{attempt+1}] generate failed: {e}", file=sys.stderr)
            continue

        payload = build_payload(region, region_type, board_slug, board_title, longtail, generated)
        try:
            result = publish(payload)
        except Exception as e:
            print(f"[#{idx}.{attempt+1}] publish failed: {e}", file=sys.stderr)
            continue

        if result is None:
            # 사전 체크 통과했는데 그래도 409 (race condition 등) → 재시도
            print(f"[#{idx}.{attempt+1}] dup at API, retrying")
            continue

        print(f"[#{idx}] published id={result.get('id')}")
        return True

    print(f"[#{idx}] all {max_retries} retries failed", file=sys.stderr)
    return False


def _slug_exists(board_slug: str, slug: str) -> bool:
    """Worker post 페이지에 HEAD 요청해 200 이면 이미 존재."""
    import requests
    site = os.environ.get("SITE_DOMAIN", "ajasky.co.kr")
    from urllib.parse import quote
    url = f"https://{site}/{quote(board_slug)}/{quote(slug)}"
    try:
        r = requests.head(url, timeout=10, allow_redirects=False)
        return r.status_code == 200
    except requests.RequestException:
        return False  # 통신 실패 시 일단 시도 (publish 단에서 409 처리됨)


def main():
    print(f"[run] start {datetime.now(timezone.utc).isoformat()}")

    # 매 cron 트리거마다 N건 발행 (PUBLISH_BATCH_SIZE).
    # 기본 1. 페이스 확장 시 2~3으로 올려 한 번에 여러 글 발행.
    batch = int(os.environ.get("PUBLISH_BATCH_SIZE", "1"))

    # 발행 확률 (시드 단계에서 변동 폭 줄이고 싶을 때 1.0; 시드 후엔 0.83~0.9).
    p = float(os.environ.get("PUBLISH_PROBABILITY", "1.0"))
    if random.random() > p:
        print(f"[skip] random skip (probability={p})")
        return

    print(f"[run] batch size = {batch}")
    success = 0
    for i in range(batch):
        if publish_one(i + 1):
            success += 1
        # 같은 cron run 안에서 Gemini API rate limit 회피 위해 약간 간격
        if i < batch - 1:
            time.sleep(random.uniform(15, 30))

    print(f"[run] done {success}/{batch} OK")
    if success == 0 and batch > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
