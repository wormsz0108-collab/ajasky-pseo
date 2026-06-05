"""키워드 변형 자동 생성.

사용자가 "관악구 스카이차", "관악구스카이차", "신림동 스카이차" 등 어떤 조합으로
쳐도 매칭되도록 메타 키워드를 자동 생성. 스팸 회피를 위해 자연스러운 변형만.
"""
from __future__ import annotations


# 광주광역시 혼동 방지로 광역 토큰 없이 한 덩어리로 쓰는 시군구 (regions.py _disambiguate 와 동기).
# "경기도광주" 채택: 네이버 실측 검색량 1위 (경기광주의 6배).
_MERGED_CITIES = {"경기도광주"}
# legacy 데이터 호환: 이미 "경기 광주시"로 저장된 글도 결합 표기로 정규화해 동일 키워드 산출.
_PROVINCE_CITY_MERGE = {("경기", "광주시"): "경기도광주"}


def _tokenize_region(region: str) -> dict[str, str]:
    """region 을 광역/시군구/동으로 분해.

    예시:
      "서울 관악구 신림동"  → {province: "서울", city: "관악구",  dong: "신림동"}
      "서울 관악구"          → {province: "서울", city: "관악구",  dong: ""}
      "서울"                  → {province: "서울", city: "",          dong: ""}
      "충북"                  → {province: "충북", city: "",          dong: ""}
      "경기 화성시 송동"      → {province: "경기", city: "화성시",  dong: "송동"}
      "경기도광주"            → {province: "",     city: "경기도광주", dong: ""}
      "경기도광주 경안동"     → {province: "",     city: "경기도광주", dong: "경안동"}
    """
    parts = region.split()
    # 결합 표기 시군구(경기도광주 등)는 광역 토큰이 없음 — 첫 토큰이 곧 city.
    if parts and parts[0] in _MERGED_CITIES:
        return {"province": "", "city": parts[0], "dong": " ".join(parts[1:])}
    # legacy "경기 광주시 ..." → 결합 표기(경기도광주)로 정규화.
    if len(parts) >= 2 and (parts[0], parts[1]) in _PROVINCE_CITY_MERGE:
        return {"province": "", "city": _PROVINCE_CITY_MERGE[(parts[0], parts[1])], "dong": " ".join(parts[2:])}
    if len(parts) >= 3:
        return {"province": parts[0], "city": parts[1], "dong": " ".join(parts[2:])}
    if len(parts) == 2:
        return {"province": parts[0], "city": parts[1], "dong": ""}
    return {"province": region, "city": "", "dong": ""}


# 여러 시에 중복되는 일반 자치구명 — leaf 로 단독 사용 시 혼동되므로 시(광역)를 붙인다.
_AMBIGUOUS_GU = {"동구", "서구", "남구", "북구", "중구"}


def _city_disp(prov: str, city: str) -> str:
    """시·군·구 표시명.
    - 경기 광주시 → '경기도광주' (광주광역시 혼동 방지)
    - 동구/서구/남구/북구/중구 → '{시} {구}' (여러 시 중복되므로 시 접두)
    """
    if prov == "경기" and city == "광주시":
        return "경기도광주"
    if city in _AMBIGUOUS_GU and prov:
        return f"{prov} {city}"
    return city


def region_leaf(region: str) -> str:
    """노출 타깃이 되는 최말단 지명(리터럴 토큰 기준). 동·읍·면 > 시·군·구 > 광역.

    "서울 강남구 압구정동"→"압구정동", "서울 관악구"→"관악구",
    "경기 광주시 곤지암읍"→"곤지암읍", "경기 광주시"→"경기도광주"(특례),
    "경기도광주 경안동"→"경안동", "세종"→"세종".
    src/lib/regions.ts 의 leafOf 와 동일 규칙.
    """
    parts = region.split()
    if not parts:
        return ""
    if len(parts) >= 3:
        return " ".join(parts[2:])
    if len(parts) == 2:
        return _city_disp(parts[0], parts[1])
    return parts[0]


def leafify(text: str, region: str) -> str:
    """제목·헤딩·본문에서 글 자신의 상위 지역 prefix 제거 → leaf 중심.

    "서울 강남구 압구정동 스카이차" → "압구정동 스카이차"
    "서울 관악구 스카이차"           → "관악구 스카이차"
    "경기 광주시 곤지암읍 스카이차"   → "곤지암읍 스카이차"
    "경기 광주시 스카이차"           → "경기도광주 스카이차"(광주 특례)
    광역 단독(세종/전북 등 1토큰)은 변경하지 않는다(leaf=광역 자체).
    인근 시군구 등 다른 지역명은 문자열이 달라 건드리지 않는다.
    """
    if not text:
        return text
    parts = region.split()
    if len(parts) < 2:                 # 광역/단일 토큰 단독 → 그대로
        return text
    if len(parts) >= 3:                # 광역 시군구 동: 광역+시군구 제거, 동 유지
        prov, city, leaf = parts[0], parts[1], " ".join(parts[2:])
        text = text.replace(f"{prov} {city} {leaf}", leaf)
        text = text.replace(f"{prov} {city}", _city_disp(prov, city))
        text = text.replace(f"{prov} {leaf}", leaf)
    else:                              # 2토큰: 광역 제거 → 시군구(광주는 결합표기)
        prov, city = parts[0], parts[1]
        text = text.replace(f"{prov} {city}", _city_disp(prov, city))
    return text


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

    # 모동(母洞): 동 어간 == 시군구 어간 이면 (구로구 구로동, 가평군 가평읍 등)
    # 결합이 "구로 구로"/"가평 가평" 처럼 중복·스팸이 되므로 결합을 생략하고
    # 동 단독("구로동", "가평읍")으로만 쓴다.
    same_stem = bool(city_full and dong_full and _strip(city_full) == _strip(dong_full))

    prefixes: list[str] = []
    # city+dong 결합 (가장 long-tail) — 모동이면 생략
    if not same_stem:
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
        if same_stem:
            most_specific_prefix = dong_full or city_full   # "가평읍" (중복 "가평 가평" 회피)
        elif city_full and dong_full:
            most_specific_prefix = f"{city_full} {dong_full}"
        else:
            most_specific_prefix = city_full or dong_full
        add(f"{most_specific_prefix} {board_title}")

    # prefix × main 조합 (메인 풀/짧음 모두)
    for prefix in prefixes:
        for m in mains:
            add(f"{prefix} {m}")

    # 상업 의도 키워드: 견적·문의 (별도 보드가 없는 의도어 — 지역 + 스카이차 + 의도).
    # 비용/가격/요금/이용료 는 각각 보드가 있어 자기 페이지끼리 경쟁 방지 위해 제외.
    COMMERCIAL_INTENTS = ("견적", "문의")
    intent_bases = [b for b in (dong_full, city_full) if b]
    if not intent_bases and r["province"]:
        intent_bases = [r["province"]]
    for base in intent_bases:
        for intent in COMMERCIAL_INTENTS:
            add(f"{base} {main_full} {intent}")

    # 스팸 회피 상한 (상업 의도어 포함 여유 위해 22)
    return kw[:22]


if __name__ == "__main__":
    # 빠른 검증
    cases = [
        ("서울 관악구 신림동", "스카이차 이용료"),
        ("서울 관악구", "스카이차 이용료"),
        ("경기 화성시 송동", "스카이차 일대"),
        ("충북", "스카이차"),
        ("인천 계양구 용종동", "고소작업차량"),
        ("충남 공주시 쌍신동", "스카이 작업차"),
        ("경기도광주", "스카이차 비용"),
        ("경기도광주 경안동", "스카이차"),
        ("경기 광주시", "스카이차 비용"),  # legacy 입력도 경기도광주로 정규화돼야 함
    ]
    for region, board in cases:
        kws = derive_keywords(region, board)
        print(f"\n[{region}] [{board}]")
        for k in kws:
            print(f"  {k}")
