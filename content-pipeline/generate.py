"""Gemini로 9-섹션 글 생성.

입력: region, board_title, longtail
출력: dict with title, meta_description, meta_keywords, body_md, toc, faq

JSON 깨짐 방지: response_schema 강제 + 다단계 복구.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai

from prompts import build_prompt

# Gemini에 강제할 응답 스키마 (response_schema 사용 시 SDK가 엄격 강제)
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "meta_description": {"type": "string"},
        "meta_keywords": {"type": "string"},
        "body_md": {"type": "string"},
        "toc": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer"},
                    "title": {"type": "string"},
                },
            },
        },
        "faq": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"q": {"type": "string"}, "a": {"type": "string"}},
                "required": ["q", "a"],
            },
        },
    },
    "required": ["title", "meta_description", "meta_keywords", "body_md", "faq"],
}


def _load_prompt(region: str, board_title: str, longtail: str) -> tuple[str, dict]:
    """다양화된 프롬프트 생성. 매 호출마다 다른 shape/제목/섹션 동의어."""
    return build_prompt(region, board_title, longtail)


def _configure_gemini() -> None:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY env var missing")
    genai.configure(api_key=key)


def _safe_resp_text(resp) -> str:
    """resp.text 가 safety block 등으로 raise할 때 대비. parts에서 직접 모음."""
    try:
        return resp.text or ""
    except Exception:
        pass
    try:
        parts = []
        for cand in (resp.candidates or []):
            content = getattr(cand, "content", None)
            for p in (getattr(content, "parts", None) or []):
                t = getattr(p, "text", None)
                if t:
                    parts.append(t)
        return "".join(parts)
    except Exception:
        return ""


def generate_post(region: str, board_title: str, longtail: str, model_name: str = "gemini-2.5-flash") -> dict[str, Any]:
    _configure_gemini()
    prompt, prompt_meta = _load_prompt(region, board_title, longtail)
    print(f"[diversity] shape={prompt_meta['shape']} n_sections={prompt_meta['n_sections']} list_count={prompt_meta['list_count']} body_len={prompt_meta['min_chars']}~{prompt_meta['max_chars']}", flush=True)
    model = genai.GenerativeModel(model_name)

    for attempt in range(3):
        raw_text = ""
        try:
            resp = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": RESPONSE_SCHEMA,
                    "temperature": 0.9,
                    "top_p": 0.95,
                },
            )
            raw_text = _safe_resp_text(resp)
            # 항상 응답 head 로깅 (디버깅용)
            print(f"[attempt {attempt+1}/3] resp len={len(raw_text)} head={raw_text[:160]!r}", flush=True)
            if not raw_text:
                raise ValueError("empty response (possibly safety blocked)")

            cleaned = _clean_json_text(raw_text)
            data = _parse_json_lenient(cleaned)
            _validate(data)
            return data
        except Exception as e:
            print(f"[attempt {attempt+1}/3] FAIL: {type(e).__name__}: {e}", flush=True)
            if attempt == 2:
                raise RuntimeError(f"Gemini failed after 3 attempts: {type(e).__name__}: {e}") from e
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _parse_json_lenient(text: str) -> dict[str, Any]:
    """다단계 복구.

    1. json.loads (정상)
    2. json_repair.repair_json (return_objects=True)
    3. body_md 부분만 따로 추출 + 나머지 정리해서 합치기 (최후 수단)
    """
    if not text:
        raise json.JSONDecodeError("empty text", text, 0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        from json_repair import repair_json
        repaired = repair_json(text, return_objects=True)
        if isinstance(repaired, dict) and repaired:
            return repaired
    except ImportError:
        print("[warn] json-repair not installed", flush=True)
    except Exception as e:
        print(f"[warn] json-repair raised: {e}", flush=True)

    # 최후 수단: 정규식으로 핵심 필드 추출
    import re
    out: dict[str, Any] = {}
    for key in ("title", "meta_description", "meta_keywords"):
        m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text)
        if m:
            out[key] = m.group(1)
    # body_md: "body_md": "..." 형태 (이스케이프 무시)
    body_match = re.search(r'"body_md"\s*:\s*"(.*?)"\s*,\s*"(?:toc|faq)"', text, re.DOTALL)
    if body_match:
        out["body_md"] = body_match.group(1).replace('\\n', '\n').replace('\\"', '"')
    # faq 추출 시도
    faq_match = re.search(r'"faq"\s*:\s*(\[.*?\])\s*}', text, re.DOTALL)
    if faq_match:
        try:
            out["faq"] = json.loads(faq_match.group(1))
        except Exception:
            try:
                from json_repair import repair_json
                rf = repair_json(faq_match.group(1), return_objects=True)
                if isinstance(rf, list):
                    out["faq"] = rf
            except Exception:
                pass
    if out:
        return out
    raise json.JSONDecodeError("all parse strategies failed", text, 0)


def _clean_json_text(text: str) -> str:
    """Gemini가 코드펜스나 leading 텍스트를 추가하는 경우 정리."""
    if not text:
        return text
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.endswith("```"):
            t = t[: -3]
        t = t.strip()
    if t.lower().startswith("json"):
        t = t[4:].lstrip(":\n ").strip()
    first = t.find("{")
    last = t.rfind("}")
    if first != -1 and last != -1 and last > first:
        t = t[first : last + 1]
    return t


REQUIRED_FIELDS = ("title", "meta_description", "meta_keywords", "body_md", "faq")


def _validate(d: dict[str, Any]) -> None:
    if not isinstance(d, dict):
        raise ValueError(f"not a dict, got {type(d).__name__}")
    for k in REQUIRED_FIELDS:
        if k not in d or not d[k]:
            raise ValueError(f"missing field: {k}")
    if len(d["title"]) > 400:
        raise ValueError("title too long")
    if len(d["meta_description"]) > 90:
        raise ValueError(f"meta_description too long ({len(d['meta_description'])}자, 네이버 80자 권장)")
    if len(d["body_md"]) > 200_000:
        raise ValueError("body_md too long")
    if not isinstance(d["faq"], list) or len(d["faq"]) < 3:
        raise ValueError("faq must be list of >=3 items")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("usage: python generate.py <region> <board_title> <longtail>")
        sys.exit(1)
    result = generate_post(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(result, ensure_ascii=False, indent=2))
