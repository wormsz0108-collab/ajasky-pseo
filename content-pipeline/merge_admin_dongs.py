"""region_dongs.py 의 충북 전역 + 세종 동 데이터 보강.

- 충북: 법정동 PDF(C:/Users/worms/Desktop/법정동_통합정리_완료/충청북도/*.pdf)에서
        11개 시군 전체 추출. 다른 지역과 동일한 깨끗한 법정동명.
        (행정동 txt 는 "봉명2송정동" 같은 합성명이 섞여 부적합 → PDF 사용.)
- 세종: 법정동 PDF 는 형식이 달라 0개 추출됨 → 행정동 txt 사용(이쪽은 깨끗).
        C:/Users/worms/Desktop/행정동/통합_최종/세종특별자치시/세종특별자치시.txt
- 서울/경기/인천/대전/충남: 손대지 않음 (extract_dongs.py PDF 추출분 유지).

세분화 동은 normalize_city_dongs 로 대표 동 정규화 + dedupe.
일회성 스크립트. 실행: python merge_admin_dongs.py
"""
from __future__ import annotations

from pathlib import Path

from dong_normalize import normalize_city_dongs
from extract_dongs import extract_dongs_from_pdf
from region_dongs import REGION_DONGS

LEGAL_PDF_ROOT = Path(r"C:/Users/worms/Desktop/법정동_통합정리_완료")
ADMIN_TXT_ROOT = Path(r"C:/Users/worms/Desktop/행정동/통합_최종")
OUT = Path(__file__).parent / "region_dongs.py"
SUFFIXES = ("동", "읍", "면")


def read_admin_txt(txt: Path) -> list[str]:
    raw = txt.read_text(encoding="utf-8-sig")
    items: list[str] = []
    for line in raw.splitlines():
        name = line.strip()
        if name.endswith(SUFFIXES) and name not in items:
            items.append(name)
    return normalize_city_dongs(items)


def main() -> None:
    # 충북 11개 시군 — 법정동 PDF에서 추출 (깨끗한 법정동명)
    cb: dict[str, list[str]] = {}
    for pdf in sorted((LEGAL_PDF_ROOT / "충청북도").glob("*.pdf")):
        dongs = normalize_city_dongs(extract_dongs_from_pdf(pdf))
        if dongs:
            cb[pdf.stem] = dongs
    REGION_DONGS["충북"] = cb

    # 세종 — 행정동 txt (법정동 PDF는 0개라 사용 불가)
    sejong_txt = ADMIN_TXT_ROOT / "세종특별자치시" / "세종특별자치시.txt"
    REGION_DONGS["세종"] = {"세종시": read_admin_txt(sejong_txt)}

    # region_dongs.py 재작성
    lines = [
        '"""동 풀 (시군구별 동/읍/면).',
        "",
        "{광역 → {시군구 → [동...]}} 구조.",
        "서울·경기·인천·대전·충남·충북: 법정동 PDF 추출(extract_dongs.py).",
        "세종: 행정동 txt 보강(merge_admin_dongs.py, 법정동 PDF 파싱 불가).",
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
    print(f"충북 {len(cb)}개 시군 {cb_total}개 동(법정동 PDF), "
          f"세종 {len(REGION_DONGS['세종']['세종시'])}개 동(행정동 txt) → {OUT}")


if __name__ == "__main__":
    main()
