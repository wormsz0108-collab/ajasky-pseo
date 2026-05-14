import { html, raw } from 'hono/html';
import type { Site, Board, Post } from '../types';
import { Layout } from './layout';
import { Thumbnail } from './thumbnail';
import type { ThumbnailText } from '../lib/thumbnail-text';

export interface RenderedSection {
  num: string;            // "01"
  anchor: string;         // "s1"
  title: string;          // "전북 스카이차 비용"
  bodyHtml: string;       // 본문 HTML (h3/p/ul/ol 포함)
}

export interface RenderedFaq { q: string; a: string }

interface PostPageProps {
  site: Site;
  boards: Pick<Board, 'slug' | 'title'>[];
  post: Pick<Post,
    'title' | 'meta_description' | 'meta_keywords' |
    'region' | 'region_type' | 'published_at' | 'modified_at' |
    'og_image_url' | 'slug'
  >;
  board: Pick<Board, 'slug' | 'title'>;
  sections: RenderedSection[];
  faq: RenderedFaq[];
  thumbnailText: ThumbnailText;
  regionChips: { name: string; href: string }[];
  jsonLd: object;
}

export function PostPage(props: PostPageProps) {
  const {
    site, boards, post, board, sections, faq,
    thumbnailText, regionChips, jsonLd,
  } = props;

  const phoneHref = `tel:${site.phone.replace(/-/g, '')}`;
  const canonicalPath = `/${encodeURIComponent(board.slug)}/${encodeURIComponent(post.slug)}`;

  const inner = html`
    <article class="wrap">

      <nav class="breadcrumb">
        <a href="/">홈</a><span class="sep">›</span>
        <a href="/${encodeURIComponent(board.slug)}">${board.title}</a><span class="sep">›</span>
        <span>${post.title}</span>
      </nav>

      <h1 class="title">${post.title}</h1>

      <div class="meta">
        <span>${formatDate(post.published_at)}</span>
        <span>·</span>
        <span>${site.site_name}</span>
        <span class="pill">${post.region}</span>
        <span class="pill">${board.title}</span>
      </div>

      ${Thumbnail({
        imageUrl: post.og_image_url || '/media/default-hero.jpg',
        ribbon: thumbnailText.ribbon,
        headlinePrefix: thumbnailText.headlinePrefix,
        headlineHighlight: thumbnailText.headlineHighlight,
        brandName: site.site_name,
        phone: site.phone,
        alt: `${post.region} ${board.title} 현장`,
      })}

      <div class="toc">
        <div class="toc-h"><span>목차</span><span class="badge">${sections.length} sections</span></div>
        <ol>
          ${sections.map(s => html`<li><a href="#${s.anchor}">${s.title}</a></li>`)}
        </ol>
      </div>

      ${sections.map((s, i) => html`
        ${i === 4 ? html`
          <div class="cta-card">
            <div class="text">
              <strong>${post.region} 현장 사진만 보내주세요</strong>
              <span>사진 3장이면 정확한 견적이 가능합니다</span>
            </div>
            <div class="btns">
              <a class="btn primary" href="${phoneHref}">전화 상담</a>
            </div>
          </div>
        ` : ''}
        <section id="${s.anchor}">
          <h2><span class="num">${s.num}</span>${s.title}</h2>
          ${raw(s.bodyHtml)}
        </section>
      `)}

      <section id="faq">
        <h2><span class="num">${pad(sections.length + 1)}</span>자주 묻는 질문</h2>
        <div class="faq">
          ${faq.map(f => html`
            <div class="faq-item">
              <p class="faq-q"><span class="qmark">Q.</span>${f.q}</p>
              <p class="faq-a">${f.a}</p>
            </div>
          `)}
        </div>
      </section>

      ${regionChips.length > 0 ? html`
        <section id="regions">
          <h2><span class="num">${pad(sections.length + 2)}</span>서비스 지역</h2>
          <p>${post.region} 인근 지역도 출장 상담 가능합니다.</p>
          <div class="region-list">
            ${regionChips.map(c => html`<a href="${c.href}">${c.name}</a>`)}
          </div>
        </section>
      ` : ''}

    </article>
  `;

  return Layout({
    site, boards,
    title: post.title,
    description: post.meta_description,
    canonicalPath,
    ogImageUrl: post.og_image_url,
    ogType: 'article',
    activeBoardSlug: board.slug,
    keywords: post.meta_keywords,
    jsonLd,
    children: inner,
  });
}

function pad(n: number) { return String(n).padStart(2, '0'); }

function formatDate(iso: string) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
}
