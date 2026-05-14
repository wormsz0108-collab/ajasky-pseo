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

export default api;
