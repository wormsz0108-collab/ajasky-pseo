import type { Env, Site } from '../types';
import { absoluteImageUrl } from '../lib/url';

// 네이버 검색엔진은 RSS 피드를 적극 활용. /rss.xml 노출 필수.
// XML 1.0 불법 제어문자(\x08 등 — Gemini 출력에 간혹 섞임)는 제거해야 피드 파서가 안 죽는다.
const stripCtl = (s: string) => s.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '');

const xmlEscape = (s: string) =>
  stripCtl(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
   .replace(/"/g, '&quot;').replace(/'/g, '&apos;');

const cdata = (s: string) => `<![CDATA[${stripCtl(s).replace(/]]>/g, ']]]]><![CDATA[>')}]]>`;

const rfc822 = (iso: string) => {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return new Date().toUTCString();
  return d.toUTCString();
};

export async function renderRss(env: Env, site: Site): Promise<string> {
  const base = `https://${site.domain}`;
  const { results } = await env.DB.prepare(
    `SELECT p.slug, p.title, p.meta_description, p.published_at, p.modified_at, p.og_image_url, p.region,
            b.slug AS board_slug, b.title AS board_title
     FROM posts p JOIN boards b ON p.board_id = b.id
     WHERE p.site_id = ? AND p.status = 'published'
     ORDER BY p.published_at DESC
     LIMIT 50`
  ).bind(site.id).all<{
    slug: string; title: string; meta_description: string;
    published_at: string; modified_at: string; og_image_url: string | null;
    region: string; board_slug: string; board_title: string;
  }>();

  const items = results.map(r => {
    const url = `${base}/${encodeURIComponent(r.board_slug)}/${encodeURIComponent(r.slug)}`;
    // enclosure url 은 RSS 2.0 스펙상 절대 URL 필수 + 한글 경로는 percent-encoding —
    // og:image(layout.tsx)·JSON-LD(jsonld.ts)와 동일하게 absoluteImageUrl 로 정규화.
    const img = absoluteImageUrl(r.og_image_url || '/og-default.jpg', site.domain);
    return `    <item>
      <title>${xmlEscape(r.title)}</title>
      <link>${xmlEscape(url)}</link>
      <guid isPermaLink="true">${xmlEscape(url)}</guid>
      <pubDate>${rfc822(r.published_at)}</pubDate>
      <category>${xmlEscape(r.board_title)}</category>
      <description>${cdata(r.meta_description)}</description>
      <enclosure url="${xmlEscape(img)}" type="image/jpeg"/>
    </item>`;
  }).join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${xmlEscape(site.site_name)}</title>
    <link>${base}/</link>
    <atom:link href="${base}/rss.xml" rel="self" type="application/rss+xml"/>
    <description>${xmlEscape(site.site_name)} 스카이차 / 고소작업차량 안내 글</description>
    <language>ko</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
${items}
  </channel>
</rss>`;
}
