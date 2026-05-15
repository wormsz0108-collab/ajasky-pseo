"""다양화된 5개 내러티브 shape 프롬프트 빌더.

각 shape는 동일 정보를 다른 구조/톤으로 전달:
  - guide       : 정보 전달형 (기본). 단계와 항목 위주.
  - case        : 사례 중심. 현장 예시 → 학습 → 일반화.
  - procedural  : 작업 절차 중심. 의뢰 → 견적 → 작업 → 마무리.
  - qa          : Q&A 중심. 질문 7~9개를 본문으로.
  - comparison  : 비교 중심. 차종/상황/시기 비교.

매 글마다 shape + 섹션 제목 동의어 + 제목 포맷 + 길이를 무작위 선택.
"""
from __future__ import annotations

from diversity import (
    pick_body_target_chars,
    pick_list_count,
    pick_n_sections,
    pick_shape,
    pick_synonym,
    pick_title_format,
)

COMMON_RULES = """엄수 규칙:
1. "렌탈" 단어 사용 절대 금지 ("일대", "이용", "사용"으로 대체)
2. 가격/비용/시간 같은 구체 수치는 단언 금지 ("달라질 수 있습니다", "~인 편이 좋습니다", "현장에 따라 조정될 수 있습니다")
3. 지역명({region})은 도입과 각 h2 섹션 첫 문장에 자연스럽게 삽입
4. h1 정확히 1개, h2는 {n_sections}개 (마지막 2개는 FAQ + 서비스지역 고정)
5. **각 h2 섹션 본문은 {min_chars}~{max_chars}자**. 깊이 있는 정보 전달 우선 — 짧으면 페널티
6. 리스트 항목은 정확히 {list_count}개
7. {longtail} 키워드를 도입과 후반부 섹션에 자연스럽게 1회씩 언급
8. 본문에 동일 문장/표현 재사용 금지 — 어휘 변화 필수
9. 광고 톤 금지, 정보·안내·경험담 톤 유지 (실제 작업자가 쓴 듯한 디테일 포함)
10. 본문 안에 큰따옴표 사용 금지 (JSON 깨짐 방지). 강조는 줄바꿈/대시·콜론으로
11. **FAQ는 반드시 10개 이상 작성**. 짧고 추상적 답변 금지 — 각 A는 최소 80자 이상, 구체적 시나리오·예시 포함
12. 각 h2 본문은 단순 나열식 X — 도입 문장 + 구체 예시 + 적용 팁 + 마무리 문장으로 단락 3~5개 구성
13. 같은 지역(시·도·시군구)·인근 지역명을 본문에 2~3회 자연 언급 (지역 SEO 시그널)
14. 차종(1톤·3.5톤·5톤), 작업 종류(외벽·간판·전기·도장·청소·이사), 현장 변수(협소 골목·옥상·고층·야간·기상)를 자연스럽게 섞어 풍부도 ↑

출력 형식: JSON 한 객체. JSON 외 텍스트 절대 금지.

JSON 스키마:
{{
  "title": "({title_format} 형식으로, 50자 이내, {region}과 {board} 모두 포함)",
  "meta_description": "(검색 결과 노출용, 반드시 80자 이내, {region} {board} 포함)",
  "meta_keywords": "(쉼표 구분, 6~8개, 첫째는 \\"{region} {board}\\")",
  "body_md": "(## 1. 제목\\n\\n본문...\\n\\n## 2. 제목\\n\\n... 형식. \\\\n 이스케이프된 문자열로 출력. 본문은 풍부하게)",
  "toc": [{{"level": 2, "title": "..."}}, ...],
  "faq": [{{"q": "...", "a": "..."}}, {{"q": "...", "a": "..."}}, ...10개 이상]
}}"""


def _guide_body_outline(region: str, board: str, longtail: str, n: int, syn: dict) -> str:
    """정보 전달 가이드형 (기본)."""
    return f"""구조 (h2 {n}개):
## 1. {region} {board} {syn['intro']}      ← {longtail} 자연 삽입, 도입
## 2. {region} {board} {syn['selection']}
  ### 체크할 점 (번호 리스트)
## 3. {region} {syn['field_check']}
  ### 체크리스트 (불릿 리스트)
## 4. {syn['procedure']}
  ### 작업 흐름 (번호 리스트)
## 5. {syn['cost']}
  ### 결정 요소 (불릿 리스트)
## 6. {syn['caution']}
  ### {syn['caution']} 정리 (불릿 리스트)
## 7. {syn['tip']}                          ← {longtail} 다시 자연 삽입, 단락 위주
## {n - 1}. {syn['faq']}                    ← Q/A 5~6쌍을 본문에 직접 (FAQ JSON에도 동일 출력)
## {n}. {syn['region']}                     ← {region} 인근 시군구 5~7개"""


def _case_body_outline(region: str, board: str, longtail: str, n: int, syn: dict) -> str:
    """사례 중심형. 현장 → 분석 → 일반화 흐름."""
    return f"""구조 (h2 {n}개) — 사례 중심:
## 1. {region} {board} {syn['intro']}                    ← 도입, {longtail} 자연 삽입
## 2. {syn['case_intro']} — {region} 현장 1               ← 가상의 현장 사례 1 (협소 골목/외벽 작업/간판 설치 중 택1)
## 3. {syn['case_lesson']}                                ← 위 사례에서 무엇을 챙겨야 했는지
  ### 사례 정리 (번호 리스트)
## 4. {region} {syn['field_check']}                       ← 일반화: 어느 현장이든 챙길 것
  ### 체크리스트 (불릿 리스트)
## 5. {syn['cost']}                                       ← 비용 결정 요소
  ### 결정 요소 (불릿 리스트)
## 6. {syn['caution']}
  ### 실수 줄이기 (불릿 리스트)
## 7. {syn['tip']}                                        ← {longtail} 다시 삽입
## {n - 1}. {syn['faq']}                                  ← Q/A 5~6쌍
## {n}. {syn['region']}                                   ← {region} 인근 시군구"""


def _procedural_body_outline(region: str, board: str, longtail: str, n: int, syn: dict) -> str:
    """절차 중심형. 의뢰부터 마무리까지 시간순."""
    return f"""구조 (h2 {n}개) — 단계별 절차:
## 1. {region} {board} {syn['intro']}                    ← 도입, {longtail} 자연 삽입
## 2. 사진 전송과 견적 문의                                ← 첫 단계
  ### 사진 잘 찍는 법 (번호 리스트)
## 3. 현장 사전 점검                                       ← 둘째 단계
  ### 체크리스트 (불릿 리스트)
## 4. 작업 당일                                             ← 셋째 단계
  ### 도착부터 시작까지 (번호 리스트)
## 5. 작업 중                                              ← 넷째 단계
  ### 안전 점검 항목 (불릿 리스트)
## 6. 작업 후 마무리                                       ← 다섯째 단계
  ### 정리 단계 (불릿 리스트)
## 7. 비용과 결제                                          ← {longtail} 자연 삽입
## {n - 1}. {syn['faq']}                                  ← Q/A 5~6쌍
## {n}. {syn['region']}                                   ← {region} 인근 시군구"""


def _qa_body_outline(region: str, board: str, longtail: str, n: int, syn: dict) -> str:
    """Q&A 중심형. 본문 자체가 큰 질문 7개."""
    n_q = max(5, n - 2)
    return f"""구조 (h2 {n}개) — Q&A 중심. 본문 각 h2가 하나의 큰 질문:
## 1. {region} {board} {syn['intro']}                    ← 도입, {longtail} 자연 삽입
## 2. Q. {region}에서 어떤 차종을 골라야 하나요?
## 3. Q. 현장 사진은 어떻게 찍어야 정확한 견적이 나오나요?
## 4. Q. 견적은 어떤 요소로 결정되나요?
## 5. Q. 야간/주말 작업도 가능한가요?
## 6. Q. 협소 골목·고층 외벽 작업은 어떻게 진행되나요?
## 7. Q. 작업 안전은 어떻게 확보되나요?                    ← {longtail} 자연 삽입
## {n - 1}. {syn['faq']}                                  ← 추가 Q/A 3~4쌍 (위와 중복 X)
## {n}. {syn['region']}                                   ← {region} 인근 시군구"""


def _comparison_body_outline(region: str, board: str, longtail: str, n: int, syn: dict) -> str:
    """비교 중심형. 차종/시간대/현장 비교."""
    return f"""구조 (h2 {n}개) — 비교 중심:
## 1. {region} {board} {syn['intro']}                    ← 도입, {longtail} 자연 삽입
## 2. {syn['comparison_a']}                              ← 1톤·소형 차량 특징
  ### 적합 현장 (불릿)
## 3. {syn['comparison_b']}                              ← 중·대형 차량 특징
  ### 적합 현장 (불릿)
## 4. {syn['comparison_choice']}                         ← 상황별 어느 쪽
  ### 상황별 정리 (번호 리스트)
## 5. {region} {syn['field_check']}
  ### 체크리스트 (불릿 리스트)
## 6. {syn['cost']}                                       ← 차종별 비용 차이 요소
  ### 결정 요소 (불릿 리스트)
## 7. {syn['caution']}                                    ← {longtail} 자연 삽입
## {n - 1}. {syn['faq']}                                  ← Q/A 5~6쌍
## {n}. {syn['region']}                                   ← {region} 인근 시군구"""


SHAPE_BUILDERS = {
    "guide": _guide_body_outline,
    "case": _case_body_outline,
    "procedural": _procedural_body_outline,
    "qa": _qa_body_outline,
    "comparison": _comparison_body_outline,
}


def build_prompt(region: str, board: str, longtail: str) -> tuple[str, dict]:
    """다양화된 프롬프트 + 메타정보 반환.

    Returns:
        (prompt_text, meta_info)
        meta_info = {"shape": "guide"|..., "n_sections": 9, ...}
    """
    shape = pick_shape()
    n_sections = pick_n_sections(default=9)
    min_chars, max_chars = pick_body_target_chars()
    list_count = pick_list_count()
    title_format = pick_title_format().format(region=region, board=board, longtail=longtail)

    # 섹션 동의어 한 번에 뽑기
    syn = {
        k: pick_synonym(k) for k in (
            "intro", "selection", "field_check", "procedure", "cost",
            "caution", "tip", "faq", "region",
            "case_intro", "case_lesson",
            "comparison_a", "comparison_b", "comparison_choice",
            "qa_block",
        )
    }

    outline = SHAPE_BUILDERS[shape](region, board, longtail, n_sections, syn)

    prompt = f"""역할: 한국어 SEO 블로그 작가 (스카이차/고소작업차량 분야, 현장 작업자 경험 톤)
목표: {region} {board} 안내 글을 {n_sections}-섹션 구조로 작성. 같은 키워드라도 매번 다른 톤·구조·표현으로.

내러티브 shape: {shape}

{outline}

{COMMON_RULES.format(
    region=region, board=board, longtail=longtail,
    n_sections=n_sections, min_chars=min_chars, max_chars=max_chars,
    list_count=list_count, title_format=title_format,
)}

입력 변수:
- region:     {region}
- board:      {board}
- longtail:   {longtail}
- 목표 제목:   {title_format}
"""
    meta = {
        "shape": shape,
        "n_sections": n_sections,
        "min_chars": min_chars,
        "max_chars": max_chars,
        "list_count": list_count,
        "title_format": title_format,
    }
    return prompt, meta
