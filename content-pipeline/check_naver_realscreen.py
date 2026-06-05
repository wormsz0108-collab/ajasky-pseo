"""실제 네이버 검색화면 기준 노출 점검 (2번 방식, 키워드 패턴별).

API(check_naver_rank.py)는 '네이버가 색인했나'를 보지만, 이건 '사람이 실제로
검색했을 때 화면에 진짜 뜨나'를 본다. search.naver.com 통합검색(nexearch) HTML을
직접 긁어서 우리 도메인이 결과에 등장하는지 + 대략 몇 번째인지 확인한다.

측정 기준 = 사람들이 실제로 치는 키워드 3패턴 (사장님 정책):
  - 시+동   ("화성 마도면 스카이차")   ← 우리가 실제로 이기는 핵심
  - 동읍면  ("마도면 스카이차")         ← 반반
  - 구/시   ("화성시 스카이차")         ← 경쟁 심해 거의 안 잡힘
("바 시/구 단독"보다 구체적인 medium-tail. 긴 longtail(광역+시+동)은 검색량 0이라 제외.)

⚠️ 공식 API가 아니라 검색화면 스크래핑이라 대량 호출 시 IP 차단(403/429) 위험.
   소량(--limit)·딜레이(--sleep)로만. 차단 감지 시 즉시 중단하고 부분결과 저장.

예:
  RANK_SITE=wormsz1.store python check_naver_realscreen.py --limit 30
  RANK_SITE=ajasky.co.kr  python check_naver_realscreen.py --limit 30 --sleep 1.5
"""
from __future__ import annotations

import argparse
import csv
import datetime
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).parent))
from keyword_variants import _tokenize_region  # noqa: E402

SITE = os.environ.get("RANK_SITE", "wormsz1.store")
WORKER_BASE = f"https://{SITE}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
_SUFFIXES = ("특별자치도", "특별자치시", "광역시", "특별시", "시", "군", "구", "동", "읍", "면")


class BlockedError(Exception):
    """네이버 차단 (403/429)."""


def strip_suffix(s: str) -> str:
    for suf in _SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            return s[:-len(suf)]
    return s


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise BlockedError(f"HTTP {e.code} — 네이버 차단. --limit 줄이거나 시간 두고 재시도.")
        raise


def _worker_auth() -> dict[str, str]:
    token = os.environ.get("WORKER_API_TOKEN")
    if not token:
        f = Path(__file__).parent.parent / ".secrets" / "worker_api_token.txt"
        if f.exists():
            token = f.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("WORKER_API_TOKEN required")
    return {"Authorization": f"Bearer {token}"}


def fetch_regions(limit: int) -> list[str]:
    """Worker 글 목록의 region 을 중복 제거하여 최대 limit 개."""
    import requests
    seen: dict[str, None] = {}
    offset = 0
    while len(seen) < limit:
        r = requests.get(f"{WORKER_BASE}/api/posts/list",
                         params={"limit": 100, "offset": offset},
                         headers=_worker_auth(), timeout=30)
        r.raise_for_status()
        page = r.json()["posts"]
        if not page:
            break
        for p in page:
            seen.setdefault(p["region"], None)
        offset += len(page)
        if len(page) < 100:
            break
    return list(seen)[:limit]


def build_patterns(region: str) -> dict[str, str | None]:
    """region → {시+동, 동읍면, 구/시} 키워드. 없으면 None."""
    t = _tokenize_region(region)
    city, dong = t["city"], t["dong"]
    city_short = strip_suffix(city) if city else ""
    return {
        "시+동": (f"{city_short} {dong} 스카이차" if city_short and dong else None),
        "동읍면": (f"{dong} 스카이차" if dong else None),
        "구/시": (f"{city} 스카이차" if city else None),
    }


def exposure(keyword: str, domain: str) -> tuple[bool, int | None]:
    """통합검색에서 (노출여부, 대략 위치). 위치는 외부(비네이버) 링크 순서."""
    url = ("https://search.naver.com/search.naver?where=nexearch&query="
           + urllib.parse.quote(keyword))
    html = http_get(url)
    if domain not in html:
        return False, None
    ext = [h for h in re.findall(r'href="(https?://[^"]+)"', html) if "naver." not in h]
    pos = next((i + 1 for i, h in enumerate(ext) if domain in h), None)
    return True, pos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30, help="점검할 지역 수(차단 방지). 지역당 최대 3검색")
    ap.add_argument("--sleep", type=float, default=1.3, help="검색 간격(초)")
    ap.add_argument("--out", default=None, help="결과 CSV 경로(기본: rank_realscreen_<site>_<날짜>.csv)")
    args = ap.parse_args()

    regions = fetch_regions(args.limit)
    out = args.out or f"rank_realscreen_{SITE}_{datetime.date.today():%Y%m%d}.csv"
    print(f"[site={SITE}] 실제 검색화면 점검 — 지역 {len(regions)}개 × 3패턴 (sleep={args.sleep}s)")
    print(f"  결과 저장 → {out}\n")

    patterns = ["시+동", "동읍면", "구/시"]
    rows: list[dict] = []
    stat = {p: {"hit": 0, "total": 0} for p in patterns}
    blocked = False

    try:
        for i, region in enumerate(regions, 1):
            kws = build_patterns(region)
            line = [f"[{i:>3}/{len(regions)}] {region}"]
            for pat in patterns:
                kw = kws[pat]
                if not kw:
                    continue
                hit, pos = exposure(kw, SITE)
                time.sleep(args.sleep)
                stat[pat]["total"] += 1
                if hit:
                    stat[pat]["hit"] += 1
                mark = (f"O({pos}번째)" if pos else "O") if hit else "X"
                line.append(f"{pat}:{mark}")
                rows.append({"region": region, "pattern": pat, "keyword": kw,
                             "exposed": int(hit), "approx_pos": pos if pos else ""})
            print("  ".join(line))
    except BlockedError as e:
        blocked = True
        print(f"\n[중단] {e}")

    # CSV 저장 (부분결과라도)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["region", "pattern", "keyword", "exposed", "approx_pos"])
        w.writeheader()
        w.writerows(rows)

    print()
    print("=" * 60)
    print(f"패턴별 실제화면 노출률 (site={SITE}){' — 부분(차단)' if blocked else ''}")
    for pat in patterns:
        s = stat[pat]
        if s["total"]:
            print(f"  {pat:<5} : {s['hit']:>3}/{s['total']:<3} ({s['hit']/s['total']*100:>4.0f}%)")
    print("=" * 60)
    print(f"CSV: {out}")


if __name__ == "__main__":
    main()
