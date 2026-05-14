-- ajasky-pseo D1 schema
-- Apply: wrangler d1 execute ajasky-pseo-db --local --file=src/db/schema.sql

PRAGMA foreign_keys = ON;

-- sites: 멀티 도메인 (도메인별 1 row)
CREATE TABLE IF NOT EXISTS sites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT UNIQUE NOT NULL,
  site_name TEXT NOT NULL,
  phone TEXT NOT NULL DEFAULT '010-9249-0510',
  logo_url TEXT,
  og_image_url TEXT,
  naver_verification TEXT,
  google_verification TEXT,
  cafe_url TEXT DEFAULT 'https://cafe.naver.com/ajasky',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- boards: 게시판 (사이트별 8개)
CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  slug TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  display_order INTEGER DEFAULT 0,
  parent_board_id INTEGER REFERENCES boards(id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(site_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_boards_site ON boards(site_id);

-- posts: 개별 글
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  slug TEXT NOT NULL,
  title TEXT NOT NULL,
  region TEXT NOT NULL,
  region_type TEXT,
  meta_description TEXT NOT NULL,
  meta_keywords TEXT NOT NULL,
  body_md TEXT NOT NULL,
  toc_json TEXT,
  faq_json TEXT,
  og_image_url TEXT,
  status TEXT DEFAULT 'published',
  published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(site_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_posts_site_board ON posts(site_id, board_id);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(site_id, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_region ON posts(site_id, region);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(site_id, status, published_at DESC);
