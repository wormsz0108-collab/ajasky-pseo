"""콘텐츠 다양화 — 네이버 D.I.A. 패턴 학습 회피.

매 글마다 무작위로:
  - 내러티브 shape (5종)
  - 섹션 제목 (각 카테고리당 5~7 동의어)
  - 글 제목 포맷 (10종)
  - 본문 길이 (±20%)
  - 리스트 항목 수 (4~7)
  - 톤 (정보전달/스토리/단계/비교/사례)
"""
from __future__ import annotations

import random

SHAPES = ["guide", "case", "procedural", "qa", "comparison"]

# 섹션 제목 동의어 풀 — 같은 의미 다른 표현
SECTION_SYNONYMS = {
    "intro": ["개요", "들어가며", "한눈에 보기", "기본 안내", "핵심 정리", "이해하기"],
    "selection": ["선택", "결정 기준", "고를 때 보는 점", "비교 포인트", "선정 가이드", "판단 기준", "차종 결정"],
    "field_check": ["현장 체크", "사전 점검", "환경 확인", "현장 답사", "출발 전 확인", "현장 정보 확인"],
    "procedure": ["진행 절차", "작업 흐름", "진행 단계", "절차 정리", "프로세스", "작업 순서"],
    "cost": ["비용 기준", "가격 산정", "비용 결정 요소", "가격 형성", "비용 가이드", "요금 산정"],
    "caution": ["주의할 점", "유의사항", "체크 포인트", "사전 확인", "실수 줄이기", "흔한 실수", "현장 리스크"],
    "tip": ["상담 팁", "문의 전 준비", "효율적인 상담", "견적 받기 전", "전화 상담 팁", "사전 준비"],
    "faq": ["자주 묻는 질문", "Q&A", "자주 받는 질문", "궁금증 정리", "흔한 질문"],
    "region": ["서비스 지역", "출장 가능 지역", "인근 권역 안내", "출장 권역", "권역 안내"],
    "case_intro": ["대표 사례", "최근 작업 사례", "현장 사례", "실제 작업 예", "사례로 보기"],
    "case_lesson": ["사례에서 배운 점", "사례가 알려주는 것", "사례 분석", "현장 교훈"],
    "comparison_a": ["1톤 차량 특징", "소형 차량 특징", "기본 차종 특징"],
    "comparison_b": ["3.5톤 이상 특징", "중·대형 차량 특징", "고소 작업차 특징"],
    "comparison_choice": ["어떤 상황에 어느 쪽", "상황별 선택", "현장별 추천"],
    "qa_block": ["자주 받는 문의", "흔히 받는 질문", "현장 자주 묻는 내용"],
}


# 글 제목 포맷 (10종) — 전부 "{region} {board}" 로 시작 (네이버 SEO: 키워드 앞쪽일수록 가중치↑)
TITLE_FORMATS = [
    "{region} {board}, {longtail}",
    "{region} {board} — {longtail}",
    "{region} {board}: {longtail}",
    "{region} {board} 안내 — {longtail}",
    "{region} {board} 알아보기 ({longtail})",
    "{region} {board} 가이드: {longtail}",
    "{region} {board} 정리 — {longtail}",
    "{region} {board} | {longtail}",
    "{region} {board} 핵심 — {longtail}",
    "{region} {board} 체크 — {longtail}",
]


# 길이/항목 변동 (네이버는 정확히 동일한 길이의 글을 의심)
# 경쟁사 분석: 8,000~9,000자 / 9 h2 ≈ 900자/h2. 우리도 매칭해야 D.I.A. 정보량 시그널 확보.
def pick_body_target_chars() -> tuple[int, int]:
    """h2 본문 1개당 목표 길이 (min, max). 매 글 변동."""
    bases = [(600, 850), (700, 950), (650, 900), (550, 800), (750, 1000)]
    return random.choice(bases)


def pick_list_count() -> int:
    return random.choice([5, 5, 6, 6, 7, 7, 8])


def pick_shape() -> str:
    return random.choice(SHAPES)


def pick_synonym(category: str) -> str:
    pool = SECTION_SYNONYMS.get(category)
    if not pool:
        return category
    return random.choice(pool)


def pick_title_format() -> str:
    return random.choice(TITLE_FORMATS)


def pick_n_sections(default: int = 9) -> int:
    """전체 섹션 수 변동. 8~10."""
    return random.choice([default - 1, default, default, default, default + 1])
