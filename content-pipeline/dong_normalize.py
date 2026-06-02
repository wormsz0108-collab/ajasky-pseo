"""세분화된 동 이름을 대표 동으로 정규화.

사장님 정책: 잘게 쪼갠 표기("법정동")로 페이지 만들지 말고 대표 동("행정동")으로 합친다.
  - 소사본동 → 소사동, 심곡본동 → 심곡동   (XX본동 → XX동)
  - 상도1동 → 상도동                         (XX숫자동 → XX동)
  - 성수1가 / 성수2가 → 성수동               (XX숫자가 → XX동)
합쳐서 같은 동이 되면 dedupe.

함정 방지: 본동/숫자동은 같은 시군구에 base 동이 실제로 있을 때만 합친다.
  - 산본동(군포) → "산동" 없음 → 그대로 (산본+동, 진짜 법정동)
  - 동본동(안성) → "동동" 없음 → 그대로
  - 본동(동작구) → 이름 자체가 "본동" → 그대로
"""
from __future__ import annotations

import re

_NUM_DONG = re.compile(r"^(.+?)\d+동$")
_NUM_GA = re.compile(r"^(.+?)\d+가$")


def _base_candidate(dong: str) -> tuple[str, bool] | None:
    """세분화 동의 대표 동 후보 → (base, 무조건합치기여부). 해당 없으면 None.

    무조건합치기=True 면 같은 시군구에 base 가 없어도 합친다(숫자+가).
    """
    m = _NUM_GA.match(dong)
    if m:
        base = m.group(1)
        base = base if base.endswith("동") else base + "동"
        return base, True  # "가"는 항상 동의 일부 → 무조건 합침
    m = _NUM_DONG.match(dong)
    if m:
        return m.group(1) + "동", False
    if dong.endswith("본동") and dong != "본동":
        return dong[:-2] + "동", False
    return None


def normalize_city_dongs(dongs: list[str]) -> list[str]:
    """한 시군구의 동 리스트를 정규화 + dedupe(순서 보존)."""
    original = set(dongs)
    out: list[str] = []
    for d in dongs:
        cand = _base_candidate(d)
        if cand:
            base, always = cand
            if always or base in original:
                d = base
        if d not in out:
            out.append(d)
    return out


if __name__ == "__main__":
    tests = {
        "동작구": ["상도동", "상도1동", "본동", "흑석동"],
        "부천시": ["소사동", "소사본동", "심곡동", "심곡본동"],
        "군포시": ["산본동", "당정동", "금정동"],
        "안성시": ["동본동", "공도읍"],
        "성동구": ["성수1가", "성수2가", "행당동"],
    }
    for city, dongs in tests.items():
        print(city, dongs, "->", normalize_city_dongs(dongs))
