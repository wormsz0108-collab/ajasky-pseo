-- ajasky-pseo seed
-- 도메인은 placeholder. 실제 도메인 받는 대로 UPDATE 또는 추가 INSERT.

INSERT OR IGNORE INTO sites (id, domain, site_name, phone) VALUES
  (1, 'ajasky.co.kr', '아자스카이', '010-9249-0510');

INSERT OR IGNORE INTO boards (site_id, slug, title, display_order) VALUES
  (1, '스카이차',         '스카이차',         1),
  (1, '스카이차-일대',     '스카이차 일대',     2),
  (1, '스카이-작업차',     '스카이 작업차',     3),
  (1, '스카이차-요금',     '스카이차 요금',     4),
  (1, '스카이차-비용',     '스카이차 비용',     5),
  (1, '스카이차-가격',     '스카이차 가격',     6),
  (1, '스카이차-이용료',   '스카이차 이용료',   7),
  (1, '고소작업차량',      '고소작업차량',      8);
