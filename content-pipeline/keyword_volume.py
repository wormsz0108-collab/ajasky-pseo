"""네이버 검색광고(파워링크) keywordstool 로 키워드별 월간검색수 조회.

목적: 추측이 아닌 실제 검색 수요로 발행 우선순위를 정한다.
  - 검색량 있는 키워드(스카이차 등) 우선 발행
  - 검색량 0(법정동 날씨 노이즈 등) 후순위/제외

자격증명 (.secrets/naver_searchad.txt 또는 환경변수):
  NAVER_AD_API_KEY   = 액세스라이선스
  NAVER_AD_SECRET    = 비밀키
  NAVER_AD_CUSTOMER  = 고객 ID

CLI:
  python keyword_volume.py 스카이차 스카이 고소작업차 고소작업차량
  python keyword_volume.py --related 스카이차 비용     # 연관 키워드까지 표시
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import time
from pathlib import Path

import requests

BASE_URL = "https://api.searchad.naver.com"
KEYWORDSTOOL_PATH = "/keywordstool"


def load_creds() -> tuple[str, str, str]:
    api_key = os.environ.get("NAVER_AD_API_KEY")
    secret = os.environ.get("NAVER_AD_SECRET")
    customer = os.environ.get("NAVER_AD_CUSTOMER")
    if not (api_key and secret and customer):
        secret_file = Path(__file__).parent.parent / ".secrets" / "naver_searchad.txt"
        if secret_file.exists():
            for line in secret_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = (x.strip() for x in line.split("=", 1))
                if k == "API_KEY":
                    api_key = api_key or v
                elif k == "SECRET_KEY":
                    secret = secret or v
                elif k == "CUSTOMER_ID":
                    customer = customer or v
    if not (api_key and secret and customer):
        raise SystemExit(
            "네이버 검색광고 자격증명 필요 — "
            "환경변수 NAVER_AD_API_KEY/NAVER_AD_SECRET/NAVER_AD_CUSTOMER "
            "또는 .secrets/naver_searchad.txt"
        )
    return api_key, secret, str(customer)


def _signature(secret: str, timestamp: str, method: str, path: str) -> str:
    msg = f"{timestamp}.{method}.{path}"
    digest = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _headers(api_key: str, secret: str, customer: str, method: str, path: str) -> dict:
    ts = str(round(time.time() * 1000))
    return {
        "X-Timestamp": ts,
        "X-API-KEY": api_key,
        "X-Customer": customer,
        "X-Signature": _signature(secret, ts, method, path),
    }


def _to_int(v) -> int:
    """monthlyPcQcCnt 가 '< 10' 같은 문자열로 올 수 있어 정수화."""
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).replace("<", "").replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        return 0


def fetch_volumes(hints: list[str], creds: tuple[str, str, str] | None = None) -> list[dict]:
    """hintKeywords(최대 5개) → 연관 키워드 + 월간검색수.

    반환: [{keyword, pc, mobile, total, comp}], total 내림차순.
    네이버는 hintKeywords 의 공백을 제거해야 하며, 결과 relKeyword 도 공백 없는 형태.
    """
    api_key, secret, customer = creds or load_creds()
    headers = _headers(api_key, secret, customer, "GET", KEYWORDSTOOL_PATH)
    hint_param = ",".join(h.replace(" ", "") for h in hints if h.strip())
    r = requests.get(
        BASE_URL + KEYWORDSTOOL_PATH,
        params={"hintKeywords": hint_param, "showDetail": 1},
        headers=headers,
        timeout=20,
    )
    r.raise_for_status()
    out: list[dict] = []
    for row in r.json().get("keywordList", []):
        pc = _to_int(row.get("monthlyPcQcCnt"))
        mo = _to_int(row.get("monthlyMobileQcCnt"))
        out.append({
            "keyword": row.get("relKeyword", ""),
            "pc": pc,
            "mobile": mo,
            "total": pc + mo,
            "comp": row.get("compIdx", ""),
        })
    out.sort(key=lambda x: x["total"], reverse=True)
    return out


def _print_table(rows: list[dict], limit: int) -> None:
    print(f"{'키워드':<24}{'월간합계':>10}{'PC':>9}{'모바일':>10}{'경쟁':>8}")
    print("-" * 64)
    for row in rows[:limit]:
        print(
            f"{row['keyword']:<24}{row['total']:>10,}{row['pc']:>9,}"
            f"{row['mobile']:>10,}{row['comp']:>8}"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description="네이버 검색광고 월간검색수 조회")
    ap.add_argument("keywords", nargs="+", help="조회할 키워드(최대 5개가 hint, 나머지는 합쳐서 1회)")
    ap.add_argument("--related", action="store_true", help="연관 키워드까지 모두 표시")
    ap.add_argument("--limit", type=int, default=30, help="표시할 행 수")
    args = ap.parse_args()

    rows = fetch_volumes(args.keywords[:5])
    if not args.related:
        hint_set = {k.replace(" ", "") for k in args.keywords}
        rows = [r for r in rows if r["keyword"].replace(" ", "") in hint_set] or rows
    _print_table(rows, args.limit)


if __name__ == "__main__":
    main()
