"""차종 제원 비교표 (GEO 강화 #1) — 발행 글마다 본문에 1개 주입.

비용/가격/요금 열은 절대 넣지 않는다 (차종+제원만). 제원 수치는 사장님이
2026-07-18 확정한 값이 유일 정답:

    차종     작업높이(최대)   작업반경
    1톤        20m            12m
    3톤      30m            23m
    5톤        45m            28m

굴절·없는 톤수(1.2·2.5·17.5·19.5톤) 및 옛 코드 잔재 높이(18m/54m/58m 등) 금지.

매 글마다(글별 해시 시드) 서로 다른 표가 나오도록 회전한다 (네이버 중복 스팸 방지):
  - 헤더 라벨 회전 (차종/차량 · 작업높이/도달높이 · 작업반경/붐 도달반경 · 대표 용도/적합 현장)
  - 열 구성 3종 변주
  - 행 순서 변주 (오름/내림)
  - 캡션·용도 서술 풀 회전 (지역명 1회 삽입 가능)

diversity.py 가 전역 random 을 쓰는 것과 달리, 이 표는 slug(=글별 키) 기반의
전용 random.Random 인스턴스로 결정적(deterministic)이다 → 같은 글은 항상 같은 표,
다른 글은 다른 표. 전역 random 상태를 건드리지 않아 다른 다양화 로직과 독립적이다.
"""
from __future__ import annotations

import random
import re

try:
    from keyword_variants import region_leaf
except Exception:  # 단독 실행/테스트 대비
    def region_leaf(r: str) -> str:  # type: ignore
        return (r or "").split(" ")[-1]


# ── 확정 제원 (유일 정답) ──────────────────────────────────────────────
# (차종 라벨, 작업높이 m, 작업반경 m)
SPECS = [
    ("1톤",   20, 12),
    ("3톤", 30, 23),
    ("5톤",   45, 28),
]

# ── 회전 풀 ───────────────────────────────────────────────────────────
H_CHAJONG = ["차종", "차량", "차종·규모", "톤수 구분"]
H_HEIGHT = ["작업높이", "최대 작업높이", "도달높이", "최대 높이"]
H_RADIUS = ["작업반경", "최대 작업반경", "작업 반경", "붐 도달반경"]
H_USE = ["대표 용도", "적합 현장", "추천 작업", "주요 현장"]

# 숫자 완충 표현 (정확 약속 회피). 표 1개당 높이/반경 각각 한 스타일로 통일.
NUM_FMT = ["최대 {n}m", "약 {n}m", "{n}m 내외", "{n}m 안팎", "{n}m급"]

# 열 구성 3종 (항상 차종으로 시작, 비용 열 없음)
COLUMN_SETS = [
    ["chajong", "height", "radius", "use"],
    ["chajong", "height", "use"],
    ["chajong", "height", "radius"],
]

# 톤수별 용도/적합 현장 서술 풀 (각 7종, 비용 단어 없음)
USE_POOL = {
    "1톤": [
        "저층 간판·주택 외벽 작업",
        "단독주택 외벽·홈통 보수",
        "저층 전기·통신 배선 작업",
        "소형 간판·저층 점검",
        "주택가 외벽 도장·청소",
        "좁은 현장 저층 작업",
        "저층 창호·차양 설치",
    ],
    "3톤": [
        "중층 건물 외벽·방수",
        "상가 간판·중층 도장",
        "중층 외벽 보수·점검",
        "중층 유리·외장 관리",
        "상가 밀집지 중층 작업",
        "중층 설비·간판 교체",
        "중규모 현장 외벽 시공",
    ],
    "5톤": [
        "고층 외벽·대형 양중",
        "고층 건물 외장·설비 작업",
        "대형 현장 자재 인양",
        "고층 도장·방수 작업",
        "대형 간판·고층 점검",
        "공장·창고 고소 작업",
        "고층 시공·중량물 인양",
    ],
}

# 접근성 서술 풀 (열 세트가 use 만 있고 radius 가 없을 때 참고용은 아님 — 현재
# 미사용이나, 향후 접근성 열 추가 대비 보존). 지금 열은 차종/높이/반경/용도.

# 캡션 풀 (7종). {region} 포함분은 지역명 1회 삽입.
CAPTION_POOL = [
    "{region} 현장에서 자주 쓰는 스카이차 차종별 제원 비교",
    "차종별 작업 높이와 적합 현장 한눈에 보기",
    "{region} 스카이차 차종 선택을 돕는 제원 정리",
    "1톤·3톤·5톤 스카이차 제원과 적합 현장",
    "현장 여건별 스카이차 차종 제원 참고표",
    "스카이차 차종별 작업 높이·작업반경 비교",
    "{region} 작업에 맞는 스카이차 차종 제원 안내",
]

# 표에 절대 있으면 안 되는 표현 (자체 게이트 — 확정 톤수 1·3·5 만 허용).
# 3.5톤: 미보유 장비라 산문·표 모두 금지(사장님 2026-07-14). 표는 3톤 통일이나
# 향후 제원 상수 오편집 대비해 자체 게이트에서도 방어적으로 차단.
_FORBIDDEN_RE = re.compile(
    r"굴절|무료|무상|0\s*원|추가\s*요금|최저가|비용|가격|요금|이용료"
    r"|1\.2\s*톤|2\.5\s*톤|3\.5\s*톤|17\.5\s*톤|19\.5\s*톤"
    r"|18\s*m|54\s*m|58\s*m"
)


def _seed(s: str) -> int:
    """djb2 — Python 프로세스 salt 무관 결정적 해시."""
    h = 5381
    for c in s.encode("utf-8"):
        h = ((h << 5) + h + c) & 0xFFFFFFFF
    return h


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def build_spec_table(seed_key: str, region: str = "") -> str:
    """글별 결정적 제원 비교표 HTML(한 줄) 생성.

    seed_key 가 같으면 같은 표, 다르면 다른 표. region 은 캡션 지역명 삽입용(선택).
    """
    rng = random.Random(_seed(seed_key))

    cols = rng.choice(COLUMN_SETS)
    labels = {
        "chajong": rng.choice(H_CHAJONG),
        "height": rng.choice(H_HEIGHT),
        "radius": rng.choice(H_RADIUS),
        "use": rng.choice(H_USE),
    }
    height_fmt = rng.choice(NUM_FMT)
    radius_fmt = rng.choice(NUM_FMT)

    # 행 순서 변주 (오름/내림). 행 개수는 3차종 고정 (미보유 차종 임의 생략 금지).
    rows = list(SPECS)
    if rng.random() < 0.5:
        rows = list(reversed(rows))

    # 톤수별 용도 서술 1개씩 픽 (표 안에서 서로 다른 인덱스 경향 위해 셔플 픽)
    use_pick = {ton: rng.choice(USE_POOL[ton]) for ton, _, _ in SPECS}

    # 캡션
    leaf = region_leaf(region) if region else ""
    caption_tpl = rng.choice(CAPTION_POOL)
    if "{region}" in caption_tpl:
        caption = caption_tpl.format(region=leaf) if leaf else \
            "스카이차 차종별 작업 높이·작업반경 비교"
    else:
        caption = caption_tpl

    # ── HTML 조립 (접근성: caption + thead th scope=col + tbody 첫칸 th scope=row) ──
    head_cells = "".join(
        f'<th scope="col">{_esc(labels[c])}</th>' for c in cols
    )
    body_rows = []
    for ton, h, r in rows:
        cells = []
        for c in cols:
            if c == "chajong":
                cells.append(f'<th scope="row">{_esc(ton)}</th>')
            elif c == "height":
                cells.append(f"<td>{_esc(height_fmt.format(n=h))}</td>")
            elif c == "radius":
                cells.append(f"<td>{_esc(radius_fmt.format(n=r))}</td>")
            elif c == "use":
                cells.append(f"<td>{_esc(use_pick[ton])}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    html = (
        '<div class="spec-table-wrap">'
        '<table class="spec-table">'
        f'<caption class="spec-caption">{_esc(caption)}</caption>'
        f"<thead><tr>{head_cells}</tr></thead>"
        f'<tbody>{"".join(body_rows)}</tbody>'
        "</table></div>"
    )

    # 자체 게이트 — 확정 제원/톤수 외 표현이 새어 들어가면 즉시 실패.
    bad = _FORBIDDEN_RE.findall(html)
    if bad:
        raise ValueError(f"spec_table forbidden tokens: {sorted(set(bad))}")
    return html


# 표를 끼워 넣을 h2 헤딩 우선순위 (차종/비교 관련 섹션 근처).
_HEADING_PREF_RE = re.compile(r"차종|차량|선택|비교|장비|작업차|고를|규모|톤")


def inject_spec_table(body_md: str, seed_key: str, region: str = "") -> str:
    """body_md 의 적절한 h2 섹션 아래에 제원 비교표(한 줄) 1개 주입.

    - 이미 주입돼 있으면(spec-table-wrap) 그대로 반환 (재실행 안전).
    - 차종/비교 관련 h2 를 우선, 없으면 2번째 h2, 없으면 1번째 h2 아래에 삽입.
    - 어떤 h2 도 없으면 원문 그대로 반환 (구조 붕괴 방지).
    """
    if "spec-table-wrap" in body_md:
        return body_md

    table = build_spec_table(seed_key, region)
    lines = body_md.replace("\r\n", "\n").split("\n")

    heading_idxs = [i for i, ln in enumerate(lines) if re.match(r"^##\s+", ln)]
    if not heading_idxs:
        return body_md  # h2 없음 — 주입 스킵

    target = None
    for i in heading_idxs:
        if _HEADING_PREF_RE.search(lines[i]):
            target = i
            break
    if target is None:
        target = heading_idxs[1] if len(heading_idxs) > 1 else heading_idxs[0]

    # 헤딩 바로 아래(그 섹션 본문 최상단)에 표 삽입.
    out = lines[: target + 1] + ["", table, ""] + lines[target + 1:]
    return "\n".join(out)


if __name__ == "__main__":
    # 간이 데모: 같은 (지역,보드) 다른 시드 5개
    for i in range(5):
        print(f"--- seed {i} ---")
        print(build_spec_table(f"서울-강남구-청담동-스카이차-demo#{i}", "서울 강남구 청담동"))
