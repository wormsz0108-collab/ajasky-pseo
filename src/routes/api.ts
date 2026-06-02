import { Hono } from 'hono';
import type { Env, Variables } from '../types';
import { verifyBearer } from '../lib/auth';

const api = new Hono<{ Bindings: Env; Variables: Variables }>();

// Bearer 인증 미들웨어 (전체 /api/*)
api.use('*', async (c, next) => {
  const expectedHash = c.env.WORKER_API_TOKEN_HASH;
  if (!expectedHash) {
    return c.json({ error: 'server_not_configured', detail: 'WORKER_API_TOKEN_HASH secret missing' }, 500);
  }
  const ok = await verifyBearer(c.req.header('authorization') ?? null, expectedHash);
  if (!ok) return c.json({ error: 'unauthorized' }, 401);
  await next();
});

api.get('/ping', (c) => c.json({ ok: true }));

// 커버리지 우선 발행용 — 사이트별 지역(region)당 발행 글 수.
// 봇이 글 수가 가장 적은 지역부터 뽑아 모든 지역을 고르게 채우는 데 사용.
api.get('/region-counts', async (c) => {
  const domain = c.req.query('site_domain');
  if (!domain) return c.json({ error: 'missing_site_domain' }, 400);
  const site = await c.env.DB.prepare('SELECT id FROM sites WHERE domain = ?')
    .bind(domain).first<{ id: number }>();
  if (!site) return c.json({ error: 'site_not_found', detail: domain }, 404);
  const { results } = await c.env.DB.prepare(
    `SELECT region, COUNT(*) as cnt FROM posts
     WHERE site_id = ? AND status = 'published'
     GROUP BY region`
  ).bind(site.id).all<{ region: string; cnt: number }>();
  const counts: Record<string, number> = {};
  for (const r of results) counts[r.region] = r.cnt;
  return c.json({ counts });
});

interface PostInput {
  site_domain: string;
  board_slug: string;
  slug: string;
  title: string;
  region: string;
  region_type?: string;
  meta_description: string;
  meta_keywords: string;
  body_md: string;
  toc_json?: string;
  faq_json?: string;
  og_image_url?: string;
  status?: 'published' | 'draft';
}

const REQUIRED = ['site_domain','board_slug','slug','title','region','meta_description','meta_keywords','body_md'] as const;

function validate(body: any): string | null {
  if (!body || typeof body !== 'object') return 'body_not_object';
  for (const k of REQUIRED) {
    if (typeof body[k] !== 'string' || !body[k].trim()) return `missing_or_empty:${k}`;
  }
  if (body.slug.length > 300) return 'slug_too_long';
  if (body.title.length > 400) return 'title_too_long';
  if (body.body_md.length > 200_000) return 'body_md_too_long';
  if (body.meta_description.length > 500) return 'meta_description_too_long';
  return null;
}

api.post('/posts', async (c) => {
  let body: PostInput;
  try { body = await c.req.json<PostInput>(); }
  catch { return c.json({ error: 'invalid_json' }, 400); }

  const err = validate(body);
  if (err) return c.json({ error: 'validation_error', detail: err }, 400);

  const site = await c.env.DB.prepare('SELECT id, domain FROM sites WHERE domain = ?')
    .bind(body.site_domain).first<{ id: number; domain: string }>();
  if (!site) return c.json({ error: 'site_not_found', detail: body.site_domain }, 404);

  const board = await c.env.DB.prepare('SELECT id, slug FROM boards WHERE site_id = ? AND slug = ?')
    .bind(site.id, body.board_slug).first<{ id: number; slug: string }>();
  if (!board) return c.json({ error: 'board_not_found', detail: body.board_slug }, 404);

  const force = c.req.query('force') === '1';
  const existing = await c.env.DB.prepare('SELECT id FROM posts WHERE site_id = ? AND slug = ?')
    .bind(site.id, body.slug).first<{ id: number }>();

  const now = new Date().toISOString();
  const status = body.status === 'draft' ? 'draft' : 'published';

  if (existing && !force) {
    return c.json({ error: 'duplicate_slug', existing_id: existing.id }, 409);
  }

  if (existing && force) {
    await c.env.DB.prepare(
      `UPDATE posts SET
         board_id=?, title=?, region=?, region_type=?,
         meta_description=?, meta_keywords=?, body_md=?,
         toc_json=?, faq_json=?, og_image_url=?, status=?, modified_at=?
       WHERE id=?`
    ).bind(
      board.id, body.title, body.region, body.region_type ?? null,
      body.meta_description, body.meta_keywords, body.body_md,
      body.toc_json ?? null, body.faq_json ?? null, body.og_image_url ?? null,
      status, now, existing.id
    ).run();
    return c.json({
      id: existing.id, updated: true,
      url: `https://${site.domain}/${encodeURIComponent(board.slug)}/${encodeURIComponent(body.slug)}`,
    });
  }

  const result = await c.env.DB.prepare(
    `INSERT INTO posts
       (site_id, board_id, slug, title, region, region_type,
        meta_description, meta_keywords, body_md,
        toc_json, faq_json, og_image_url, status, published_at, modified_at)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`
  ).bind(
    site.id, board.id, body.slug, body.title, body.region, body.region_type ?? null,
    body.meta_description, body.meta_keywords, body.body_md,
    body.toc_json ?? null, body.faq_json ?? null, body.og_image_url ?? null,
    status, now, now
  ).run();

  return c.json({
    id: result.meta.last_row_id,
    url: `https://${site.domain}/${encodeURIComponent(board.slug)}/${encodeURIComponent(body.slug)}`,
  }, 201);
});

api.delete('/posts/:id{[0-9]+}', async (c) => {
  const id = parseInt(c.req.param('id'), 10);
  const r = await c.env.DB.prepare('DELETE FROM posts WHERE id = ?').bind(id).run();
  if (r.meta.changes === 0) return c.json({ error: 'not_found' }, 404);
  return c.json({ deleted: id });
});

// OG 이미지 업로드 — R2 PutObject가 Python boto3에서 AccessDenied이므로 Worker 경유.
// body는 JPG raw bytes, query: slug, 선택적 variant (body1/body2/body3 등).
//   - 기본 (variant 없음): R2 키 = "og/{slug}.jpg" (hero)
//   - variant 있음:        R2 키 = "og/{variant}-{slug}.jpg" (본문 변형)
api.post('/og-upload', async (c) => {
  const slug = c.req.query('slug');
  if (!slug || slug.length > 300) return c.json({ error: 'invalid_slug' }, 400);
  const variant = c.req.query('variant') ?? '';
  if (variant && !/^[a-z0-9-]{1,20}$/.test(variant)) {
    return c.json({ error: 'invalid_variant' }, 400);
  }
  const body = await c.req.arrayBuffer();
  if (body.byteLength < 1000 || body.byteLength > 2_000_000) {
    return c.json({ error: 'invalid_size', size: body.byteLength }, 400);
  }
  const key = variant ? `og/${variant}-${slug}.jpg` : `og/${slug}.jpg`;
  await c.env.MEDIA.put(key, body, {
    httpMetadata: {
      contentType: 'image/jpeg',
      cacheControl: 'public, max-age=2592000, immutable',
    },
  });
  return c.json({ url: `/media/${key}` });
});

// 백필 — og_image 재합성 대상 목록.
// ?missing_og=1 → 아직 raw photo 가리키는 글만. ?limit=N&offset=M 페이지네이션.
api.get('/posts/list', async (c) => {
  const missingOg = c.req.query('missing_og') === '1';
  const limit = Math.min(100, Math.max(1, parseInt(c.req.query('limit') ?? '20', 10)));
  const offset = Math.max(0, parseInt(c.req.query('offset') ?? '0', 10));

  const where = missingOg
    ? "WHERE p.status='published' AND (p.og_image_url IS NULL OR p.og_image_url LIKE '/media/photos/%' OR p.og_image_url LIKE '/media/default-%')"
    : "WHERE p.status='published'";

  const { results } = await c.env.DB.prepare(
    `SELECT p.id, p.slug, p.region, p.og_image_url, p.meta_keywords,
            b.slug as board_slug, b.title as board_title,
            s.domain as site_domain
     FROM posts p
     JOIN boards b ON p.board_id = b.id
     JOIN sites s ON p.site_id = s.id
     ${where}
     ORDER BY p.id ASC
     LIMIT ? OFFSET ?`
  ).bind(limit, offset).all<{
    id: number; slug: string; region: string; og_image_url: string | null;
    meta_keywords: string | null;
    board_slug: string; board_title: string; site_domain: string;
  }>();

  return c.json({ posts: results, limit, offset });
});

// 백필 — meta_keywords 갱신.
api.patch('/posts/:id{[0-9]+}/keywords', async (c) => {
  const id = parseInt(c.req.param('id'), 10);
  let body: { meta_keywords?: string };
  try { body = await c.req.json(); }
  catch { return c.json({ error: 'invalid_json' }, 400); }
  const kw = body.meta_keywords;
  if (typeof kw !== 'string' || !kw.trim() || kw.length > 500) {
    return c.json({ error: 'invalid_keywords' }, 400);
  }
  const r = await c.env.DB.prepare(
    'UPDATE posts SET meta_keywords = ?, modified_at = ? WHERE id = ?'
  ).bind(kw, new Date().toISOString(), id).run();
  if (r.meta.changes === 0) return c.json({ error: 'not_found' }, 404);
  return c.json({ id, meta_keywords: kw });
});

// 백필 — og_image_url 만 갱신.
api.patch('/posts/:id{[0-9]+}/og', async (c) => {
  const id = parseInt(c.req.param('id'), 10);
  let body: { og_image_url?: string };
  try { body = await c.req.json(); }
  catch { return c.json({ error: 'invalid_json' }, 400); }
  const url = body.og_image_url;
  if (typeof url !== 'string' || !url.startsWith('/media/')) {
    return c.json({ error: 'invalid_og_url' }, 400);
  }
  const r = await c.env.DB.prepare(
    'UPDATE posts SET og_image_url = ?, modified_at = ? WHERE id = ?'
  ).bind(url, new Date().toISOString(), id).run();
  if (r.meta.changes === 0) return c.json({ error: 'not_found' }, 404);
  return c.json({ id, og_image_url: url });
});

export default api;
