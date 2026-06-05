-- rank_history 테이블 추가 (네이버 순위 측정 이력)
-- Apply(remote): wrangler d1 execute ajasky-pseo-db --remote --file=src/db/migrate-rank.sql
-- 추가형(CREATE IF NOT EXISTS) — 기존 데이터에 영향 없음.
CREATE TABLE IF NOT EXISTS rank_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
  query TEXT NOT NULL,
  rank INTEGER,
  matched_url TEXT,
  total_results INTEGER,
  checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rank_post ON rank_history(post_id, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_rank_site ON rank_history(site_id, checked_at DESC);
