-- 신규 보드 3종 추가 (2026-07-16 사장님 확정 — 검색량 실측 기반 보드 교체).
--
-- 배경: "스카이차 일대/이용료/요금" 은 실검색어가 아니라서 신규 발행 축을
--   "스카이차 임대 / 스카이차 업체 / 근처 스카이차" 로 교체.
--   단 기존 발행 글 6,300여 개와 그 URL·보드(title·slug)는 절대 불변 —
--   옛 보드 3종은 UPDATE 하지 않고(rename 금지) 신규 3종을 INSERT 만 한다.
--   ("대여"는 금지어 — "임대"만 사용.)
--
-- 대상: ajasky.co.kr, wormsz1.store 두 사이트 모두.
-- display_order 는 기존(1~8) 뒤인 9~11.
-- UNIQUE(site_id, slug) + INSERT OR IGNORE 로 재실행해도 안전(멱등).
--
-- 적용(코디네이터가 CF MCP 또는 wrangler 로 실행 — 파이프라인 가동 전 선행 필수):
--   wrangler d1 execute ajasky-pseo-db --remote --file=src/db/add-boards-2026-07-16.sql
--
-- 검증:
--   SELECT s.domain, b.slug, b.title, b.display_order
--   FROM boards b JOIN sites s ON b.site_id = s.id
--   WHERE s.domain IN ('ajasky.co.kr','wormsz1.store')
--   ORDER BY s.domain, b.display_order;
--   → 도메인당 11행 (기존 8 + 신규 3) 이어야 함.

INSERT OR IGNORE INTO boards (site_id, slug, title, display_order)
SELECT s.id, b.slug, b.title, b.display_order
FROM sites s
JOIN (
  SELECT '스카이차-임대' AS slug, '스카이차 임대' AS title, 9 AS display_order
  UNION ALL SELECT '스카이차-업체', '스카이차 업체', 10
  UNION ALL SELECT '근처-스카이차', '근처 스카이차', 11
) b
WHERE s.domain IN ('ajasky.co.kr', 'wormsz1.store');
