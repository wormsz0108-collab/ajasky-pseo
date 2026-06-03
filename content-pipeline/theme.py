"""도메인별 OG 색 테마. 웹 크롬 테마(src/templates/theme.ts)와 동일한 djb2 해시·
순서를 써서, 도메인마다 웹과 OG 이미지 색이 자동으로 일치한다.

순서는 theme.ts 의 THEMES 와 반드시 동일해야 함: [0]=핑크, [1]=블루, [2]=틸.
도메인은 ASCII 라 JS charCodeAt == Python ord → 해시 결과 동일.
"""
from __future__ import annotations


def _djb2(s: str) -> int:
    h = 5381
    for ch in s:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF  # JS의 >>> 0 (32bit unsigned) 재현
    return h


# 각 테마가 정의하는 색: 좌측 띠 / 리본 / 헤드라인 밑줄 / 하단 바 / 브랜드명 / 점
OG_THEMES = [
    {  # 0 — 핑크 (기존 시그니처)
        "side": "#ffd200", "ribbon": "#ec4899", "underline": "#ffd200",
        "bar": "#000000", "name": "#ffd200", "dot": "#ec4899",
    },
    {  # 1 — 블루
        "side": "#2563eb", "ribbon": "#f59e0b", "underline": "#38bdf8",
        "bar": "#0f172a", "name": "#38bdf8", "dot": "#f59e0b",
    },
    {  # 2 — 틸/그린
        "side": "#0d9488", "ribbon": "#f43f5e", "underline": "#facc15",
        "bar": "#042f2e", "name": "#5eead4", "dot": "#f43f5e",
    },
]


def pick_og_theme(domain: str) -> dict:
    return OG_THEMES[_djb2(domain) % len(OG_THEMES)]


# 도메인별 OG 합성 구성(레이아웃·색). 여기 없는 도메인은 기존 시그니처(좌측 띠·핑크)
# 그대로 유지 → wormsz1.store 등은 건드리지 않음.
#   layout="panel"     : 하단 패널형 (사진 강조 + 하단 그라데이션). accent 색 사용.
#   layout="signature" : 기존 좌측 노란 띠형. theme(OG_THEMES dict) 또는 None(핑크).
SITE_OG = {
    "ajasky.co.kr": {"layout": "panel", "accent": "#2563eb"},
}


def og_config(domain: str) -> dict:
    return SITE_OG.get(domain, {"layout": "signature", "theme": None})
