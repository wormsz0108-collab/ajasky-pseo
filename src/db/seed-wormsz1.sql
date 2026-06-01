-- wormsz1.store 사이트 추가 (site_id=2)
-- ajasky.co.kr 과 동일 설정(브랜드/전화/보드 8개). 신뢰도 높은 wormsz1.store가
-- 같은 키워드에서 ajasky.co.kr 을 자연스럽게 이기도록 (전략 B = 본진 교체).
-- Apply(remote): wrangler d1 execute ajasky-pseo-db --remote --file=src/db/seed-wormsz1.sql
--
-- naver_verification 은 서치어드바이저에서 wormsz1.store 등록 후 발급코드로 UPDATE.
--   UPDATE sites SET naver_verification='<코드>' WHERE domain='wormsz1.store';

INSERT OR IGNORE INTO sites (domain, site_name, phone) VALUES
  ('wormsz1.store', '아자스카이', '010-9249-0510');

INSERT OR IGNORE INTO boards (site_id, slug, title, display_order)
SELECT s.id, b.slug, b.title, b.display_order
FROM sites s
JOIN (
  SELECT '스카이차'        AS slug, '스카이차'        AS title, 1 AS display_order
  UNION ALL SELECT '스카이차-일대',   '스카이차 일대',   2
  UNION ALL SELECT '스카이-작업차',   '스카이 작업차',   3
  UNION ALL SELECT '스카이차-요금',   '스카이차 요금',   4
  UNION ALL SELECT '스카이차-비용',   '스카이차 비용',   5
  UNION ALL SELECT '스카이차-가격',   '스카이차 가격',   6
  UNION ALL SELECT '스카이차-이용료', '스카이차 이용료', 7
  UNION ALL SELECT '고소작업차량',    '고소작업차량',    8
) b
WHERE s.domain = 'wormsz1.store';
