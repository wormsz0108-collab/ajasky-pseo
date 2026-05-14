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
            text = _clean_json_text(resp.text)
            data = _parse_json_lenient(text)
            _validate(data)
            return data
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[attempt {attempt+1}/3] parse fail: {e}; raw head: {(resp.text or '')[:200]!r}", flush=True)
            if attempt == 2:
                raise RuntimeError(f"Gemini parse failed after retries: {e}") from e
            time.sleep(2 ** attempt)
        except Exception as e:
            print(f"[attempt {attempt+1}/3] exception: {e}", flush=True)
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _parse_json_lenient(text: str) -> dict[str, Any]:
    """엄격 파싱 실패 시 json-repair 로 복구. Gemini가 가끔 body_md 안에 raw \\n을 넣어 깨먹음."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json
        except ImportError as e:
            raise json.JSONDecodeError(f"strict parse failed and json-repair missing: {e}", text, 0)
        repaired = repair_json(text, return_objects=True)
        if not isinstance(repaired, dict):
            raise json.JSONDecodeError("repair did not yield object", text, 0)
        return repaired


def _clean_json_text(text: str) -> str:
    """Gemini가 가끔 ```json ... ``` 코드펜스나 leading text를 추가하는 경우 정리.

    또한 body_md 안의 raw newline이 json.loads 깨먹는 경우를 위해 마지막 폴백으로
    `{` ... `}` 구간만 추출.
    """
    if not text:
        return text
    t = text.strip()
    # ```json … ``` 펜스 제거
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.endswith("```"):
            t = t[: -3]
        t = t.strip()
    # 한 번 더 leading "json" 등 흔적 제거
    if t.lower().startswith("json"):
        t = t[4:].lstrip(":\n ").strip()
    # 첫 { … 마지막 } 만 추출 (앞뒤 잡설 제거)
    first = t.find("{")
    last = t.rfind("}")
    if first != -1 and last != -1 and last > first:
        t = t[first : last + 1]
    return t


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
