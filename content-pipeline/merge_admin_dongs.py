"""행정동 txt 소스로 region_dongs.py 의 충북 전역 + 세종 동 데이터 보강.

소스: C:/Users/worms/Desktop/행정동/통합_최종/{도}/{시군구}.txt (UTF-8 BOM, 한 줄 1동)
- 충북: PDF 추출본은 청주·충주만 있어 나머지 9개 시군 누락 → 11개 시군 전체로 교체.
- 세종: 동데이터 0 → 세종특별자치시.txt 로 채움 (city 키 "세종시").
- 서울/경기/인천/대전/충남은 건드리지 않음 (이미 완비).

세분화 동은 normalize_city_dongs 로 대표 동 정규화 + dedupe.
일회성 스크립트. 실행: python merge_admin_dongs.py
"""
from __future__ import annotations

from pathlib import Path

from dong_normalize import normalize_city_dongs
from region_dongs import REGION_DONGS

SRC = Path(r"C:/Users/worms/Desktop/행정동/통합_최종")
OUT = Path(__file__).parent / "region_dongs.py"
SUFFIXES = ("동", "읍", "면")


def read_dongs(txt: Path) -> list[str]:
    raw = txt.read_text(encoding="utf-8-sig")
    items: list[str] = []
    for line in raw.splitlines():
        name = line.strip()
        if name.endswith(SUFFIXES) and name not in items:
            items.append(name)
    return normalize_city_dongs(items)


def main() -> None:
    # 충북 11개 시군 전체 교체
    cb_dir = SRC / "충청북도"
    cb: dict[str, list[str]] = {}
    for txt in sorted(cb_dir.glob("*.txt")):
        cb[txt.stem] = read_dongs(txt)
    REGION_DONGS["충북"] = cb

    # 세종: 단일 파일 → city 키 "세종시"
    sejong_txt = SRC / "세종특별자치시" / "세종특별자치시.txt"
    REGION_DONGS["세종"] = {"세종시": read_dongs(sejong_txt)}

    # region_dongs.py 재작성 (extract_dongs.py 와 동일 포맷)
    lines = [
        '"""법정동/행정동 동 풀.',
        "",
        "{광역 → {시군구 → [동...]}} 구조.",
        "서울·경기·인천·대전·충남: 법정동 PDF 추출(extract_dongs.py).",
        "충북·세종: 행정동 txt 보강(merge_admin_dongs.py).",
        '"""',
        "",
        "REGION_DONGS = {",
    ]
    for label, cities in REGION_DONGS.items():
        lines.append(f'    "{label}": {{')
        for city, dongs in cities.items():
            joined = ", ".join(f'"{d}"' for d in dongs)
            lines.append(f'        "{city}": [{joined}],')
        lines.append("    },")
    lines.append("}")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")

    cb_total = sum(len(v) for v in cb.values())
    print(f"충북 {len(cb)}개 시군 {cb_total}개 동, 세종 {len(REGION_DONGS['세종']['세종시'])}개 동 → {OUT}")


if __name__ == "__main__":
    main()
