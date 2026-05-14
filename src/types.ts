export interface Env {
  DB: D1Database;
  MEDIA: R2Bucket;
  WORKER_API_TOKEN_HASH: string;
}

export interface Site {
  id: number;
  domain: string;
  site_name: string;
  phone: string;
  logo_url: string | null;
  og_image_url: string | null;
  naver_verification: string | null;
  google_verification: string | null;
  cafe_url: string | null;
  created_at: string;
}

export interface Board {
  id: number;
  site_id: number;
  slug: string;
  title: string;
  description: string | null;
  display_order: number;
  parent_board_id: number | null;
  created_at: string;
}

export interface Post {
  id: number;
  site_id: number;
  board_id: number;
  slug: string;
  title: string;
  region: string;
  region_type: string | null;
  meta_description: string;
  meta_keywords: string;
  body_md: string;
  toc_json: string | null;
  faq_json: string | null;
  og_image_url: string | null;
  status: string;
  published_at: string;
  modified_at: string;
}

export type Variables = {
  site: Site;
};
