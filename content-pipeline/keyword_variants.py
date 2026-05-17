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
    """region + board → 사장님 PowerLink 패턴 그대로 (최대 20개, 중복 제거).

    패턴 (사장님 정책):
      - 광역(경기/충북 등) 접두는 제외
      - A 시군: 풀/짧음 (가평군 / 가평)
      - B 구:   풀/짧음 (강남구 / 강남)
      - C 동읍면: 풀/짧음 (가평읍 / 가평, 신림동 / 신림)
      - 메인: 스카이차 / 스카이 (보드별: 고소작업차량 / 고소작업차)
    """
    r = _tokenize_region(region)
    board_main, board_specific = _board_parts(board_title)

    kw: list[str] = []

    def add(s: str) -> None:
        s = s.strip()
        if s and s not in kw:
            kw.append(s)

    # 메인 키워드 변형: 풀 + 짧음 ("스카이차" → "스카이", "고소작업차량" → "고소작업차")
    SHORT_MAIN_MAP = {
        "스카이차": "스카이",
        "고소작업차량": "고소작업차",
    }
    main_full = board_main                                 # "스카이차"
    main_short = SHORT_MAIN_MAP.get(board_main, "")       # "스카이"
    mains = [m for m in (main_full, main_short) if m]

    # 접미사 떼서 짧은 형태: "화성시" → "화성", "신림동" → "신림", "향남읍" → "향남"
    def _strip(s: str) -> str:
        for suf in ("특별자치도", "특별자치시", "광역시", "특별시", "시", "군", "구", "동", "읍", "면"):
            if s.endswith(suf) and len(s) > len(suf):
                return s[:-len(suf)]
        return s

    city_full = r["city"]                                  # "가평군" / "강남구" / "화성시"
    city_short = _strip(city_full) if city_full else ""    # "가평" / "강남" / "화성"
    dong_full = r["dong"]                                  # "가평읍" / "신림동"
    dong_short = _strip(dong_full) if dong_full else ""    # "가평" / "신림"
    # 1글자 약어는 일반 단어 충돌 우려 ("송" 등) — 2글자 이상만
    if len(city_short) < 2:
        city_short = ""
    if len(dong_short) < 2:
        dong_short = ""

    # 접두사 후보: city(full/short), dong(full/short), city+dong (full/short combo)
    # — 광역(province) 은 제외
    city_variants = [c for c in (city_full, city_short) if c]
    dong_variants = [d for d in (dong_full, dong_short) if d]

    prefixes: list[str] = []
    # city+dong 결합 (가장 long-tail)
    for c in city_variants:
        for d in dong_variants:
            prefixes.append(f"{c} {d}")
    # dong 단독
    prefixes.extend(dong_variants)
    # city 단독
    prefixes.extend(city_variants)
    # 광역만 있는 글(예: 지역="경기"/"세종") fallback — 광역을 prefix 로 사용
    if not city_variants and not dong_variants and r["province"]:
        prefixes.append(r["province"])

    # board_specific 가 있는 경우 (예: "스카이차 이용료") — 가장 구체적인 long-tail 1개 추가
    if board_specific and city_variants:
        most_specific_prefix = (
            f"{city_full} {dong_full}" if (city_full and dong_full)
            else (city_full or dong_full)
        )
        add(f"{most_specific_prefix} {board_title}")

    # prefix × main 조합 (메인 풀/짧음 모두)
    for prefix in prefixes:
        for m in mains:
            add(f"{prefix} {m}")

    # 최대 20개로 자름 (스팸 위험 회피)
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
