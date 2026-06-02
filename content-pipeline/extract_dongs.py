"""법정동 PDF에서 동 이름 추출 → region_dongs.py 데이터 파일 생성.

일회성 스크립트. 사장님 PC 로컬에서 실행.

사용법:
    cd content-pipeline
    python extract_dongs.py
"""
from __future__ import annotations

from pathlib import Path

import pdfplumber

from dong_normalize import normalize_city_dongs

SRC_ROOT = Path(r"C:/Users/worms/Desktop/법정동_통합정리_완료")
OUT_PATH = Path(__file__).parent / "region_dongs.py"

# 발행 대상 지역 (regions.py 의 all_region_targets() 와 동기)
TARGET = {
    "서울특별시":   {"all": True,  "label": "서울"},
    "경기도":       {"all": True,  "label": "경기"},
    "인천광역시":   {"all": True,  "label": "인천"},
    "세종특별자치시": {"all": True, "label": "세종"},
    "대전광역시":   {"all": True,  "label": "대전"},
    "충청남도":     {"all": True,  "label": "충남"},
    "충청북도":     {"all": False, "label": "충북", "cities": {"청주시", "충주시"}},
}


def extract_dongs_from_pdf(pdf_path: Path) -> list[str]:
    """PDF 한 장에서 마지막 토큰(법정동/읍/면) 모음.

    동 외에도 읍/면도 행정 단위라 검색 대상에 포함 (예: 화성시 향남읍, 양평군 양서면).
    """
    SUFFIXES = ("동", "읍", "면")
    items: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                parts = line.strip().split()
                if len(parts) >= 3 and parts[-1].endswith(SUFFIXES):
                    item = parts[-1]
                    if item not in items:
                        items.append(item)
    return items


def main():
    result: dict[str, dict[str, list[str]]] = {}
    total = 0
    for folder_name, cfg in TARGET.items():
        folder = SRC_ROOT / folder_name
        if not folder.exists():
            print(f"[skip] {folder} not found")
            continue
        label = cfg["label"]
        result.setdefault(label, {})
        for pdf in sorted(folder.glob("*.pdf")):
            city = pdf.stem  # ex "강남구"
            if not cfg["all"] and city not in cfg.get("cities", set()):
                continue
            dongs = extract_dongs_from_pdf(pdf)
            dongs = normalize_city_dongs(dongs)  # 세분화 동 → 대표 동 정규화 + dedupe
            if dongs:
                result[label][city] = dongs
                total += len(dongs)
                print(f"  {label} {city}: {len(dongs)}개")
            else:
                print(f"  [warn] {label} {city}: 0 dongs extracted")

    # Python 모듈 형태로 저장
    out_lines = [
        '"""법정동 풀 (PDF에서 자동 추출, extract_dongs.py 결과).',
        "",
        "{광역 → {시군구 → [법정동...]}} 구조.",
        "',발행 대상 지역의 모든 동' 만 포함.",
        '"""',
        "",
        "REGION_DONGS = {",
    ]
    for label, cities in result.items():
        out_lines.append(f'    "{label}": {{')
        for city, dongs in cities.items():
            joined = ", ".join(f'"{d}"' for d in dongs)
            out_lines.append(f'        "{city}": [{joined}],')
        out_lines.append("    },")
    out_lines.append("}")
    out_lines.append("")
    OUT_PATH.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\n총 {total}개 법정동 추출 → {OUT_PATH}")


if __name__ == "__main__":
    main()
