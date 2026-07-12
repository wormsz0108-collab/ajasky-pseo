"""Gemini로 9-섹션 글 생성.

입력: region, board_title, longtail
출력: dict with title, meta_description, meta_keywords, body_md, toc, faq

JSON 깨짐 방지: response_schema 강제 + 다단계 복구.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from prompts import build_prompt
from keyword_variants import leafify, region_leaf

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


def _make_client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY env var missing")
    return genai.Client(api_key=key)


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
    client = _make_client()
    prompt, prompt_meta = _load_prompt(region, board_title, longtail)
    print(f"[diversity] shape={prompt_meta['shape']} n_sections={prompt_meta['n_sections']} list_count={prompt_meta['list_count']} body_len={prompt_meta['min_chars']}~{prompt_meta['max_chars']}", flush=True)

    # thinking 토큰이 비용의 ~2/3 (실측). 9-섹션 구조는 thinking 없이도 유지되므로 기본 0(끔).
    # 품질 보강 필요 시 env GEMINI_THINKING_BUDGET 로 256~1024 부여 가능.
    thinking_budget = int(os.environ.get("GEMINI_THINKING_BUDGET", "0"))
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
        temperature=0.9,
        top_p=0.95,
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
    )

    for attempt in range(3):
        raw_text = ""
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            raw_text = _safe_resp_text(resp)
            # 항상 응답 head 로깅 (디버깅용)
            print(f"[attempt {attempt+1}/3] resp len={len(raw_text)} head={raw_text[:160]!r}", flush=True)
            if not raw_text:
                raise ValueError("empty response (possibly safety blocked)")

            cleaned = _clean_json_text(raw_text)
            data = _parse_json_lenient(cleaned)
            # 노출 타깃 일치: 제목(H1)·메타설명·본문(H2/H3·산문)의 상위 지역 prefix 제거
            # → "서울 강남구 압구정동 …" 을 "압구정동 …" 으로. (인근 시군구 등 타 지역명은 유지)
            # 검증보다 먼저 — 제목 leaf-시작 검사와 표기가 일치해야 함.
            for k in ("title", "meta_description", "body_md"):
                if data.get(k):
                    data[k] = leafify(data[k], region)
            _validate(data, region)
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

# 라이브 발행 전 콘텐츠 게이트 — 프롬프트 규칙만으로는 temp 0.9 에서 확률적으로 새어
# 나옴(실측: 발행분 5,786건 중 렌탈 58·무료 68·추가요금없음 16건 등 ~2% 누출).
# 매치 시 ValueError → generate_post 가 새 출력으로 재시도(최대 3회).
#   렌탈           : 사업 절대 금지어
#   무료/0원/추가요금없음/도착시간 : 지키지 못할 절대약속 표현 금지
#   주간과 동일     : 야간·주말 금액 다름 명시 규칙 위반
#   윤재근         : 대표 본명 노출 금지
#   날씨           : 기상 화제 금지 (무관 검색 유입 방지)
BANNED_RE = re.compile(
    r"렌탈|무료|무상|0\s*원|추가\s*요금\s*없|추가요금\s*없|요금\s*없이|비용\s*없이"
    r"|\d+\s*분\s*내?\s*도착|즉시\s*도착|주간과\s*동일|윤재근|날씨"
)

# Gemini 가 간혹 섞는 제어문자(\x08 등) — RSS/sitemap XML 파싱 실패·SERP title 오염 원인.
_CTRL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _banned_hits(d: dict[str, Any]) -> list[str]:
    texts = [d.get("title", ""), d.get("meta_description", ""), d.get("meta_keywords", ""), d.get("body_md", "")]
    for f in d.get("faq") or []:
        if isinstance(f, dict):
            texts.append(f.get("q", ""))
            texts.append(f.get("a", ""))
    hits: list[str] = []
    for t in texts:
        hits.extend(BANNED_RE.findall(t or ""))
    return hits


def _validate(d: dict[str, Any], region: str = "") -> None:
    if not isinstance(d, dict):
        raise ValueError(f"not a dict, got {type(d).__name__}")
    for k in REQUIRED_FIELDS:
        if k not in d or not d[k]:
            raise ValueError(f"missing field: {k}")

    # 제어문자는 거부 대신 제거 (콘텐츠 자체는 정상인 경우가 대부분)
    for k in ("title", "meta_description", "meta_keywords", "body_md"):
        if isinstance(d.get(k), str):
            d[k] = _CTRL_RE.sub("", d[k])

    if len(d["title"]) > 80:
        raise ValueError(f"title too long ({len(d['title'])}자, 규칙 50자)")
    leaf = region_leaf(region) if region else ""
    if leaf and not d["title"].lstrip().startswith(leaf):
        raise ValueError(f"title must start with leaf {leaf!r}: {d['title'][:40]!r}")
    if len(d["meta_description"]) > 90:
        raise ValueError(f"meta_description too long ({len(d['meta_description'])}자, 네이버 80자 권장)")
    body = d["body_md"]
    if len(body) > 200_000:
        raise ValueError("body_md too long")
    # 잘린 출력(정규식 fallback 등) 차단 — 짧은 thin content 가 slug 를 선점하면 재발행도 막힘
    if len(body) < 2_000:
        raise ValueError(f"body_md too short ({len(body)}자) — 잘린 출력 의심")
    if len(re.findall(r"(?m)^##\s", body)) < 6:
        raise ValueError("body_md h2 heading < 6 — 섹션 구조 붕괴")
    if not isinstance(d["faq"], list) or len(d["faq"]) < 3:
        raise ValueError("faq must be list of >=3 items")

    hits = _banned_hits(d)
    if hits:
        raise ValueError(f"banned words: {sorted(set(hits))}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("usage: python generate.py <region> <board_title> <longtail>")
        sys.exit(1)
    result = generate_post(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(result, ensure_ascii=False, indent=2))
