"""키워드 변형 자동 생성.

사용자가 "관악구 스카이차", "관악구스카이차", "신림동 스카이차" 등 어떤 조합으로
쳐도 매칭되도록 메타 키워드를 자동 생성. 스팸 회피를 위해 자연스러운 변형만.
"""
from __future__ import annotations


def _tokenize_region(region: str) -> dict[str, str]:
    """region 을 광역/시군구/동으로 분해.

    예시:
      "서울 관악구 신림동"  → {province: "서울", city: "관악구",  dong: "신림동"}
      "서울 관악구"          → {province: "서울", city: "관악구",  dong: ""}
      "서울"                  → {province: "서울", city: "",          dong: ""}
      "충북"                  → {province: "충북", city: "",          dong: ""}
      "경기 화성시 송동"      → {province: "경기", city: "화성시",  dong: "송동"}
    """
    parts = region.split()
    if len(parts) >= 3:
        return {"province": parts[0], "city": parts[1], "dong": " ".join(parts[2:])}
    if len(parts) == 2:
        return {"province": parts[0], "city": parts[1], "dong": ""}
    return {"province": region, "city": "", "dong": ""}


def _board_parts(board_title: str) -> tuple[str, str]:
    """보드 → (main, specific). '스카이차 이용료' → ('스카이차', '이용료').

    "스카이 작업차"는 특수 케이스: main = "스카이차" (단독 "스카이" 금지 정책).
    단어가 1개면 specific = "" 반환.
    """
    # 사장님 정책: "스카이" 단독 키워드 금지 — 항상 "스카이차"로 통일.
    BOARD_MAIN_OVERRIDE = {
        "스카이 작업차": ("스카이차", "작업차"),
        "고소작업차량":   ("고소작업차량", ""),
    }
    if board_title in BOARD_MAIN_OVERRIDE:
        return BOARD_MAIN_OVERRIDE[board_title]
    parts = board_title.split(maxsplit=1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], ""


def derive_keywords(region: str, board_title: str) -> list[str]:
    """region + board → 자연스러운 키워드 변형 리스트 (중복 제거, 8~10개).

    사장님 정책: 브랜드("아자스카이")는 meta_keywords 에 넣지 않음.
    """
    r = _tokenize_region(region)
    board_main, board_specific = _board_parts(board_title)

    kw: list[str] = []

    def add(s: str) -> None:
        s = s.strip()
        if s and s not in kw:
            kw.append(s)

    # 사용자는 종종 키워드 끝 글자 생략하고 검색: "스카이차" → "스카이", "고소작업차량" → "고소작업차"
    # 매칭용 보조 변형만 추가. 우리 글 제목/본문 디자인은 항상 풀표기 유지.
    SHORT_MAIN_MAP = {
        "스카이차": "스카이",
        "고소작업차량": "고소작업차",
    }
    short_main = SHORT_MAIN_MAP.get(board_main, "")

    # 시/군/구/동/읍/면 접미사 떼면 더 짧은 형태로도 검색됨
    # ("화성시" → "화성", "신림동" → "신림", "향남읍" → "향남", "남양읍" → "남양")
    def _strip(s: str) -> str:
        for suf in ("특별자치도", "특별자치시", "광역시", "특별시", "시", "군", "구", "동", "읍", "면"):
            if s.endswith(suf) and len(s) > len(suf):
                return s[:-len(suf)]
        return s

    city_full = r["city"]                                  # "화성시"
    city_short = _strip(city_full) if city_full else ""    # "화성"
    dong_full = r["dong"]                                  # "신림동"
    dong_short = _strip(dong_full) if dong_full else ""    # "신림"
    # 1글자 약어는 일반 단어와 충돌 우려 ("송" → 의미 너무 약함). 2글자 이상만 사용.
    if len(city_short) < 2:
        city_short = ""
    if len(dong_short) < 2:
        dong_short = ""

    def add_combos(prefix: str) -> None:
        """prefix + (board_title / board_main / short_main) × (띄움 / 붙임)"""
        if not prefix:
            return
        # 풀 보드 (e.g., "스카이차 이용료")는 띄움 형태만 — 붙임은 부자연
        if board_specific:
            add(f"{prefix} {board_title}")
        # board_main: 띄움 + 붙임
        add(f"{prefix} {board_main}")
        add(f"{prefix}{board_main}")
        # short_main: 띄움 + 붙임
        if short_main:
            add(f"{prefix} {short_main}")
            add(f"{prefix}{short_main}")

    # 1) 풀 표기 (region + board_title)
    add(f"{region} {board_title}")

    # 2) 시군구(full)부터 시작 (광역 생략) — 가장 흔한 검색 패턴
    if city_full:
        if dong_full:
            add(f"{city_full} {dong_full} {board_title}")  # "화성시 송동 스카이차 일대"
        else:
            add(f"{city_full} {board_title}")              # "화성시 스카이차 일대"

    # 3) 동(洞) 변형 — 풀/짧음 × 띄움/붙임 × 메인/숏메인
    if dong_full:
        add_combos(dong_full)                              # 신림동 *
    if dong_short and dong_short != dong_full:
        add_combos(dong_short)                             # 신림 *

    # 4) 시군구 변형 — 풀/짧음 × 띄움/붙임 × 메인/숏메인
    if city_full:
        add_combos(city_full)                              # 화성시 *
    if city_short and city_short != city_full:
        add_combos(city_short)                             # 화성 *

    # 5) 보드 자체
    add(board_title)                                       # "스카이차 이용료"
    if board_specific:
        add(board_main)                                    # "스카이차"

    # 6) 광역 + 보드 메인
    if r["province"] and r["province"] != city_full:
        add(f"{r['province']} {board_main}")               # "서울 스카이차"

    # 7) 최대 20개로 자름 (스팸 위험 회피 — 30+ 부터 패널티)
    return kw[:20]


if __name__ == "__main__":
    # 빠른 검증
    cases = [
        ("서울 관악구 신림동", "스카이차 이용료"),
        ("서울 관악구", "스카이차 이용료"),
        ("경기 화성시 송동", "스카이차 일대"),
        ("충북", "스카이차"),
        ("인천 계양구 용종동", "고소작업차량"),
        ("충남 공주시 쌍신동", "스카이 작업차"),
    ]
    for region, board in cases:
        kws = derive_keywords(region, board)
        print(f"\n[{region}] [{board}]")
        for k in kws:
            print(f"  {k}")
