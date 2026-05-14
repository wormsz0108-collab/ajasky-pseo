import type { Env, Site } from '../types';

export const POSTS_PER_SITEMAP = 1000;

const xmlEscape = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
   .replace(/"/g, '&quot;').replace(/'/g, '&apos;');

const urlFor = (site: Site, path: string) =>
  `https://${site.domain}${path.startsWith('/') ? '' : '/'}${encodeURI(path)}`;

const nowIso = () => new Date().toISOString();

interface UrlEntry {
  loc: string;
  lastmod?: string;
  changefreq?: 'always' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'never';
  priority?: number;
}

export function buildUrlSet(entries: UrlEntry[]): string {
  const items = entries.map(e => {
    const parts = [`<loc>${xmlEscape(e.loc)}</loc>`];
    if (e.lastmod) parts.push(`<lastmod>${xmlEscape(e.lastmod)}</lastmod>`);
    if (e.changefreq) parts.push(`<changefreq>${e.changefreq}</changefreq>`);
    if (e.priority !== undefined) parts.push(`<priority>${e.priority.toFixed(1)}</priority>`);
    return `  <url>\n    ${parts.join('\n    ')}\n  </url>`;
  }).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap-0.9">
${items}
</urlset>`;
}

export function buildSitemapIndex(maps: { loc: string; lastmod?: string }[]): string {
  const items = maps.map(m => {
    const parts = [`<loc>${xmlEscape(m.loc)}</loc>`];
    if (m.lastmod) parts.push(`<lastmod>${xmlEscape(m.lastmod)}</lastmod>`);
    return `  <sitemap>\n    ${parts.join('\n    ')}\n  </sitemap>`;
  }).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap-0.9">
${items}
</sitemapindex>`;
}

// 인덱스: pages-1 + boards-1 + posts-1..N
export async function renderSitemapIndex(env: Env, site: Site): Promise<string> {
  const row = await env.DB.prepare(
    `SELECT COUNT(*) as c, MAX(modified_at) as m FROM posts
     WHERE site_id = ? AND status = 'published'`
  ).bind(site.id).first<{ c: number; m: string | null }>();
  const total = row?.c ?? 0;
  const postsLastmod = row?.m ?? nowIso();
  const numPostSitemaps = Math.max(1, Math.ceil(total / POSTS_PER_SITEMAP));
  const today = nowIso();

  const maps: { loc: string; lastmod?: string }[] = [
    { loc: urlFor(site, '/sitemap-pages-1.xml'), lastmod: today },
    { loc: urlFor(site, '/sitemap-boards-1.xml'), lastmod: today },
  ];
  if (total > 0) {
    for (let i = 1; i <= numPostSitemaps; i++) {
      maps.push({ loc: urlFor(site, `/sitemap-posts-${i}.xml`), lastmod: postsLastmod });
    }
  }
  return buildSitemapIndex(maps);
}

export function renderPagesSitemap(site: Site): string {
  return buildUrlSet([
    { loc: urlFor(site, '/'), changefreq: 'daily', priority: 1.0, lastmod: nowIso() },
  ]);
}

export async function renderBoardsSitemap(env: Env, site: Site): Promise<string> {
  const { results } = await env.DB.prepare(
    'SELECT slug FROM boards WHERE site_id = ? ORDER BY display_order'
  ).bind(site.id).all<{ slug: string }>();
  const entries: UrlEntry[] = results.map(b => ({
    loc: urlFor(site, `/${b.slug}`),
    changefreq: 'weekly',
    priority: 0.8,
    lastmod: nowIso(),
  }));
  return buildUrlSet(entries);
}

export async function renderPostsSitemap(env: Env, site: Site, n: number): Promise<string | null> {
  if (n < 1) return null;
  const offset = (n - 1) * POSTS_PER_SITEMAP;
  const { results } = await env.DB.prepare(
    `SELECT p.slug, p.modified_at, b.slug AS board_slug
     FROM posts p JOIN boards b ON p.board_id = b.id
     WHERE p.site_id = ? AND p.status = 'published'
     ORDER BY p.id
     LIMIT ? OFFSET ?`
  ).bind(site.id, POSTS_PER_SITEMAP, offset).all<{ slug: string; modified_at: string; board_slug: string }>();

  if (results.length === 0 && n > 1) return null;
  const entries: UrlEntry[] = results.map(r => ({
    loc: urlFor(site, `/${r.board_slug}/${r.slug}`),
    lastmod: r.modified_at,
    changefreq: 'monthly',
    priority: 0.6,
  }));
  return buildUrlSet(entries);
}
