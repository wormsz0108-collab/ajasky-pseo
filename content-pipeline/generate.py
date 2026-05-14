"""Gemini로 9-섹션 글 생성.

입력: region, board_title, longtail
출력: dict with title, meta_description, meta_keywords, body_md, toc, faq
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai

PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompt-template.txt"


def _load_prompt(region: str, board_title: str, longtail: str) -> str:
    raw = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return raw.format(region=region, board_title=board_title, longtail=longtail)


def _configure_gemini() -> None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY env var missing")
    genai.configure(api_key=key)


def generate_post(region: str, board_title: str, longtail: str, model_name: str = "gemini-2.5-flash") -> dict[str, Any]:
    _configure_gemini()
    prompt = _load_prompt(region, board_title, longtail)
    model = genai.GenerativeModel(model_name)

    for attempt in range(3):
        try:
            resp = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.9,
                    "top_p": 0.95,
                },
            )
            text = resp.text
            data = json.loads(text)
            _validate(data)
            return data
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            if attempt == 2:
                raise RuntimeError(f"Gemini parse failed after retries: {e}") from e
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


REQUIRED_FIELDS = ("title", "meta_description", "meta_keywords", "body_md", "faq")


def _validate(d: dict[str, Any]) -> None:
    for k in REQUIRED_FIELDS:
        if k not in d or not d[k]:
            raise ValueError(f"missing field: {k}")
    if len(d["title"]) > 400:
        raise ValueError("title too long")
    # 네이버 SA 권장: meta description 80자 이내. 살짝 여유는 두지만 90 넘으면 재시도.
    if len(d["meta_description"]) > 90:
        raise ValueError(f"meta_description too long ({len(d['meta_description'])}자, 네이버 80자 권장)")
    if len(d["body_md"]) > 200_000:
        raise ValueError("body_md too long")
    if not isinstance(d["faq"], list) or len(d["faq"]) < 3:
        raise ValueError("faq must be list of >=3 items")


if __name__ == "__main__":
    # 단독 실행 시 샘플 1건 생성하고 출력 (디버그용)
    import sys
    if len(sys.argv) < 4:
        print("usage: python generate.py <region> <board_title> <longtail>")
        sys.exit(1)
    result = generate_post(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(result, ensure_ascii=False, indent=2))
