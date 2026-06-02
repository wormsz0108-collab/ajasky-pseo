import { Hono } from 'hono';
import type { Env, Site, Board, Post, Variables } from './types';
import { HomePage } from './templates/home';
import { BoardPage } from './templates/board';
import { PostPage } from './templates/post';
import { buildArticleJsonLd, buildHomeJsonLd, buildBoardJsonLd } from './seo/jsonld';
import {
  renderSitemapIndex, renderPagesSitemap, renderBoardsSitemap, renderPostsSitemap,
} from './seo/sitemap';
import { renderRobots } from './seo/robots';
import { renderRss } from './seo/rss';
import { FAVICON_PNG } from './favicon';
import { buildThumbnailText } from './lib/thumbnail-text';
import { parseBodyMarkdown } from './lib/markdown';
import { pickBodyPhotos } from './lib/body-photos';
import { NotFoundPage } from './templates/notfound';
import apiRoutes from './routes/api';
import { cityOf } from './lib/regions';
import {
  buildDummyPost, buildDummySections, buildDummyFaq,
} from './lib/dummy';
import { recoveryCron } from './cron/recovery';

const POSTS_PER_PAGE = 20;

const app = new Hono<{ Bindings: Env; Variables: Variables }>();

// Host 헤더로 site 분기 (dev 환경 fallback 포함)
app.use('*', async (c, next) => {
  const rawHost = c.req.header('host') ?? '';
  const host = rawHost.split(':')[0].toLowerCase();

  let site = await c.env.DB.prepare('SELECT * FROM sites WHERE domain = ?')
    .bind(host)
    .first<Site>();

  if (!site && (host === 'localhost' || host === '127.0.0.1' || host.endsWith('.workers.dev'))) {
    site = await c.env.DB.prepare('SELECT * FROM sites WHERE id = 1').first<Site>();
  }

  if (!site) return c.text(`Site not found: ${host}`, 404);
  c.set('site', site);
  await next();
});

app.get('/_health', (c) => c.json({ ok: true, ts: Date.now() }));

// REST API (Python publish.py 발행 엔드포인트)
app.route('/api', apiRoutes);

// ----- SEO endpoints -----
const xmlHeaders = { 'content-type': 'application/xml; charset=utf-8', 'cache-control': 'public, max-age=300, s-maxage=60' };

app.get('/sitemap.xml', async (c) => {
  const xml = await renderSitemapIndex(c.env, c.get('site'));
  return new Response(xml, { headers: xmlHeaders });
});
app.get('/sitemap-pages-1.xml', (c) => new Response(renderPagesSitemap(c.get('site')), { headers: xmlHeaders }));
app.get('/sitemap-boards-1.xml', async (c) => {
  const xml = await renderBoardsSitemap(c.env, c.get('site'));
  return new Response(xml, { headers: xmlHeaders });
});
// /sitemap-posts-N.xml — Hono 라우트 param + literal suffix 충돌 회피 위해 :boardSlug 핸들러 안에서 처리

app.get('/robots.txt', (c) =>
  new Response(renderRobots(c.get('site')), {
    headers: { 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'public, max-age=86400' },
  })
);

app.get('/rss.xml', async (c) => {
  const xml = await renderRss(c.env, c.get('site'));
  return new Response(xml, {
    headers: { 'content-type': 'application/rss+xml; charset=utf-8', 'cache-control': 'public, max-age=1800' },
  });
});

// R2 미디어 서빙 (커스텀 도메인 붙기 전까지 Worker 경유)
app.get('/media/:key{.+}', async (c) => {
  const key = c.req.param('key');
  const obj = await c.env.MEDIA.get(key);
  if (!obj) return c.text('Not found', 404);
  const headers = new Headers();
  obj.writeHttpMetadata(headers);
  headers.set('cache-control', 'public, max-age=2592000, immutable');
  headers.set('etag', obj.httpEtag);
  return new Response(obj.body, { headers });
});

// 파비콘 (Worker 내장 — 전 도메인 공통). /favicon.ico, /favicon.png 모두 PNG로 서빙.
const faviconResponse = () => new Response(FAVICON_PNG, {
  headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=2592000, immutable' },
});
app.get('/favicon.ico', () => faviconResponse());
app.get('/favicon.png', () => faviconResponse());

// 홈
app.get('/', async (c) => {
  const site = c.get('site');
  const boards = await getBoards(c.env, site.id);
  const recents = await c.env.DB.prepare(
    `SELECT p.slug, p.title, p.region, p.published_at, p.og_image_url,
            b.slug as board_slug, b.title as board_title
     FROM posts p JOIN boards b ON p.board_id = b.id
     WHERE p.site_id = ? AND p.status = 'published'
     ORDER BY p.published_at DESC LIMIT 12`
  ).bind(site.id).all<any>();

  const recentPosts = recents.results.map(r => ({
    board_slug: r.board_slug,
    board_title: r.board_title,
    slug: r.slug,
    title: r.title,
    region: r.region,
    published_at: r.published_at,
    og_image_url: r.og_image_url,
    thumbnailText: buildThumbnailText(r.region, r.board_title),
  }));

  const jsonLd = buildHomeJsonLd(site);
  return c.html(HomePage({ site, boards, recentPosts, jsonLd }) as any);
});

// 보드
app.get('/:boardSlug', async (c) => {
  const site = c.get('site');
  const boardSlug = decodeURIComponent(c.req.param('boardSlug'));

  // /sitemap-posts-N.xml fallback (Hono regex 라우트 quirk 우회)
  const postSitemapMatch = boardSlug.match(/^sitemap-posts-(\d+)\.xml$/);
  if (postSitemapMatch) {
    const n = parseInt(postSitemapMatch[1], 10);
    const xml = await renderPostsSitemap(c.env, c.get('site'), n);
    if (xml === null) return c.text('Not found', 404);
    return new Response(xml, { headers: xmlHeaders });
  }

  if (
    boardSlug.startsWith('_') ||
    boardSlug.includes('.') ||
    boardSlug === 'media' ||
    boardSlug === 'robots' ||
    boardSlug === 'rss' ||
    boardSlug === 'sitemap' ||
    boardSlug === 'api'
  ) {
    return c.notFound();
  }

  const board = await c.env.DB.prepare(
    'SELECT id, slug, title, description FROM boards WHERE site_id = ? AND slug = ?'
  ).bind(site.id, boardSlug).first<Board>();
  if (!board) return c.notFound();

  const boards = await getBoards(c.env, site.id);
  const page = Math.max(1, parseInt(c.req.query('page') ?? '1', 10));
  const offset = (page - 1) * POSTS_PER_PAGE;

  const { results: postRows } = await c.env.DB.prepare(
    `SELECT slug, title, region, published_at, og_image_url
     FROM posts WHERE site_id = ? AND board_id = ? AND status = 'published'
     ORDER BY published_at DESC LIMIT ? OFFSET ?`
  ).bind(site.id, board.id, POSTS_PER_PAGE, offset).all<any>();

  const countRow = await c.env.DB.prepare(
    `SELECT COUNT(*) as c FROM posts WHERE site_id = ? AND board_id = ? AND status = 'published'`
  ).bind(site.id, board.id).first<{ c: number }>();
  const total = countRow?.c ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / POSTS_PER_PAGE));

  const posts = postRows.map(r => ({
    ...r,
    thumbnailText: buildThumbnailText(r.region, board.title),
  }));

  const jsonLd = buildBoardJsonLd({ site, board, posts: postRows.map(r => ({ title: r.title, slug: r.slug })) });
  return c.html(BoardPage({ site, boards, board, posts, page, totalPages, jsonLd }) as any);
});

// 글
app.get('/:boardSlug/:postSlug', async (c) => {
  const site = c.get('site');
  const boardSlug = decodeURIComponent(c.req.param('boardSlug'));
  const postSlug = decodeURIComponent(c.req.param('postSlug'));

  // 엣지 캐시: 글 페이지는 거의 안 바뀌므로 Cache API 로 1시간 캐시.
  // (홈·보드는 새 글 즉시 반영 위해 캐시 안 함.) Host 가 URL에 포함돼 도메인별 분리됨.
  const cache = caches.default;
  const cacheKey = new Request(c.req.url, { method: 'GET' });
  const cached = await cache.match(cacheKey);
  if (cached) return cached;

  const board = await c.env.DB.prepare(
    'SELECT id, slug, title, description FROM boards WHERE site_id = ? AND slug = ?'
  ).bind(site.id, boardSlug).first<Board>();
  if (!board) return c.notFound();

  const boards = await getBoards(c.env, site.id);

  const post = await c.env.DB.prepare(
    `SELECT * FROM posts WHERE site_id = ? AND board_id = ? AND slug = ? AND status = 'published'`
  ).bind(site.id, board.id, postSlug).first<Post>();

  // 같은 보드 다른 글 풀 — 한 번에 60개 랜덤. 현재 글 제외.
  // 7개는 "같은 보드 다른 안내"(클러스터), 나머지는 "서비스 지역" 칩의 실제 내부링크 소스로 재사용.
  const poolRows = await c.env.DB.prepare(
    `SELECT slug, title, region FROM posts
     WHERE site_id = ? AND board_id = ? AND status = 'published' AND slug != ?
     ORDER BY RANDOM() LIMIT 60`
  ).bind(site.id, board.id, postSlug).all<{ slug: string; title: string; region: string }>();
  const pool = poolRows.results;
  const sameBoardPosts = pool.slice(0, 7);

  if (!post) {
    // DB에 없는 slug = 404. 시안용 dummy fallback 제거 (publish 파이프라인의 사전 체크가 이걸 의존).
    return c.notFound();
  }

  // body_md 마크다운 파서 → 9-섹션 추출. 파싱 실패 시 dummy fallback.
  let sections = parseBodyMarkdown(post.body_md);
  if (sections.length < 3) {
    sections = buildDummySections(post.region, board.title);
  }
  const resp = renderPost({
    site, boards, board, post,
    sections,
    faq: post.faq_json ? safeJsonParse(post.faq_json) : buildDummyFaq(post.region, board.title),
    sameBoardPosts,
    pool,
  });
  // 엣지 캐시에 저장 (응답 반환은 막지 않도록 waitUntil).
  c.executionCtx.waitUntil(cache.put(cacheKey, resp.clone()));
  return resp;
});

function renderPost(opts: {
  site: Site; boards: Pick<Board, 'slug'|'title'>[]; board: Board;
  post: Post; sections: ReturnType<typeof buildDummySections>;
  faq: { q: string; a: string }[];
  sameBoardPosts: { slug: string; title: string; region: string }[];
  pool: { slug: string; title: string; region: string }[];
}) {
  const { site, boards, board, post, sections, faq, sameBoardPosts, pool } = opts;
  const jsonLd = buildArticleJsonLd({ site, board, post, faq });

  // "서비스 지역" 칩 = 같은 보드의 실제 인근 지역 글로 내부링크 (시군구 1개당 1글, 최대 24).
  // 기존엔 50개가 전부 보드 목록으로 링크 → 색인/내부링크 시그널 약했음.
  const seenCity = new Set<string>([cityOf(post.region)]);
  const regionChips: { name: string; href: string }[] = [];
  for (const r of pool) {
    const city = cityOf(r.region);
    if (!city || seenCity.has(city)) continue;
    seenCity.add(city);
    regionChips.push({
      name: city,
      href: `/${encodeURIComponent(board.slug)}/${encodeURIComponent(r.slug)}`,
    });
    if (regionChips.length >= 24) break;
  }

  const bodyPhotos = pickBodyPhotos(post.slug, post.region, board.title);
  const relatedBoards = boards.filter(b => b.slug !== board.slug);

  return new Response(
    PostPage({
      site, boards, board, post,
      sections, faq,
      thumbnailText: buildThumbnailText(post.region, board.title),
      regionChips,
      bodyPhotos,
      relatedBoards,
      sameBoardPosts,
      jsonLd,
    }).toString(),
    { headers: {
      'content-type': 'text/html; charset=utf-8',
      // 브라우저 10분, 엣지(Cache API/CDN) 1시간. 글은 거의 안 바뀜.
      'cache-control': 'public, max-age=600, s-maxage=3600',
    } }
  );
}

async function getBoards(env: Env, siteId: number) {
  const { results } = await env.DB.prepare(
    'SELECT id, slug, title, description FROM boards WHERE site_id = ? ORDER BY display_order'
  ).bind(siteId).all<Board>();
  return results;
}

function safeJsonParse<T>(s: string): T | any {
  try { return JSON.parse(s); } catch { return [] as any; }
}

// 404 — 사이트 컨텍스트 살아있는 상태에서 디자인된 404 페이지 렌더
app.notFound(async (c) => {
  const site = c.get('site');
  if (!site) return c.text('Not found', 404);
  const boards = await getBoards(c.env, site.id);
  const html = NotFoundPage({ site, boards, attemptedPath: new URL(c.req.url).pathname }).toString();
  return new Response(html, { status: 404, headers: { 'content-type': 'text/html; charset=utf-8' } });
});

export default {
  fetch: app.fetch.bind(app),
  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil(recoveryCron(env));
  },
};
