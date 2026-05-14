"""Worker REST API에 글 POST."""
from __future__ import annotations

import json
import os
import random
import time
from typing import Any

import requests


def slugify_ko(text: str) -> str:
    """한글 + 영문 + 숫자만 남기고 공백→하이픈. URL은 어차피 percent-encoded.

    예: "전북 스카이차 비용 사진 가이드" → "전북-스카이차-비용-사진-가이드"
    """
    cleaned = []
    for ch in text:
        if ch.isalnum() or ch in "가나다라마바사아자차카타파하":
            cleaned.append(ch)
        elif "가" <= ch <= "힣":  # 한글 음절
            cleaned.append(ch)
        elif ch in " -_/":
            cleaned.append("-")
    s = "".join(cleaned)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")[:280]


def publish(payload: dict[str, Any], retries: int = 3) -> dict[str, Any] | None:
    api_url = os.environ.get("WORKER_API", "https://ajasky.co.kr/api/posts")
    token = os.environ.get("WORKER_API_TOKEN")
    if not token:
        raise RuntimeError("WORKER_API_TOKEN env var missing")

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.post(
                api_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            if r.status_code == 409:
                print(f"[skip] duplicate slug: {payload['slug']}")
                return None
            if r.status_code == 401:
                raise RuntimeError("unauthorized — WORKER_API_TOKEN 잘못됨")
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_err = e
            if attempt == retries - 1:
                break
            time.sleep(2 ** attempt + random.random())
    raise RuntimeError(f"publish failed after {retries} retries: {last_err}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("usage: python publish.py <payload.json>")
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        payload = json.load(f)
    result = publish(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
