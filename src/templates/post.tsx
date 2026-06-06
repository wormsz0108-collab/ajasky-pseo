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
  bodyPhotos: { url: string; caption: string }[];   // 본문 중간 삽입 사진 (slug 해시 결정적)
  relatedBoards: { slug: string; title: string }[]; // 다른 보드 cross-link
  sameBoardPosts: { slug: string; title: string; region: string }[]; // 같은 보드 다른 글 (클러스터)
  jsonLd: object;
}

export function PostPage(props: PostPageProps) {
  const {
    site, boards, post, board, sections, faq,
    thumbnailText, regionChips, bodyPhotos, relatedBoards, sameBoardPosts, jsonLd,
  } = props;

  const phoneHref = `tel:${site.phone.replace(/-/g, '')}`;
  const canonicalPath = `/${encodeURIComponent(board.slug)}/${encodeURIComponent(post.slug)}`;

  // 본문에 FAQ 동의어 섹션(궁금증 정리 등)이 있으면 그 자리에 실제 Q&A를 넣고
  // 하단 중복 FAQ 섹션은 생략 — '빈 FAQ 섹션' 문제 해결.
  const FAQ_TITLE_RE = /자주\s*(?:묻는|받는|받|묻)|궁금증|Q\s*&\s*A|흔한\s*질문|흔히\s*받는|현장\s*자주/;
  const faqHostIdx = faq.length > 0 ? sections.findIndex(s => FAQ_TITLE_RE.test(s.title)) : -1;
  const hasStandaloneFaq = faqHostIdx === -1 && faq.length > 0;

  const faqItems = html`<div class="faq">
    ${faq.map(f => html`
      <div class="faq-item">
        <p class="faq-q"><span class="qmark">Q.</span>${f.q}</p>
        <p class="faq-a">${f.a}</p>
      </div>
    `)}
  </div>`;

  // 섹션 번호는 실제로 렌더되는 섹션만 세어 연속되게 매김.
  // (옵션 섹션이 비면 번호가 건너뛰던 버그 수정 — 예: 10→12)
  let secNum = sections.length;
  const faqNum = hasStandaloneFaq ? pad(++secNum) : '';
  const sameBoardNum = sameBoardPosts.length > 0 ? pad(++secNum) : '';
  const regionsNum = regionChips.length > 0 ? pad(++secNum) : '';
  const relatedNum = relatedBoards.length > 0 ? pad(++secNum) : '';

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
        imageUrl: post.og_image_url || '/media/photos/001.jpg',
        ribbon: thumbnailText.ribbon,
        headlinePrefix: thumbnailText.headlinePrefix,
        headlineHighlight: thumbnailText.headlineHighlight,
        brandName: site.site_name,
        phone: site.phone,
        alt: `${post.region} ${board.title} 스카이차 작업 현장`,
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
          ${i === faqHostIdx ? faqItems : ''}
          ${[1, 3, 5].includes(i) ? Thumbnail({
            // 본문 3장 모두 브랜디드 — 같은 디자인/텍스트, 배경 사진만 변형 (body1/body2/body3).
            // R2 키: og/s{site_id}/body{N}-{slug}.jpg (사이트별). 미생성분은 /media 가
            // 옛 공유 키(og/body{N}-{slug}.jpg)로 폴백하므로 재합성 전에도 404 안 남.
            imageUrl: `/media/og/s${site.id}/body${(i + 1) / 2}-${post.slug}.jpg`,
            ribbon: thumbnailText.ribbon,
            headlinePrefix: thumbnailText.headlinePrefix,
            headlineHighlight: thumbnailText.headlineHighlight,
            brandName: site.site_name,
            phone: site.phone,
            // 본문 3장 각각 구분되는 설명형 alt (중복 alt 방지).
            alt: `${post.region} ${board.title} ${['작업 현장', '장비 안내', '시공 사례'][(i + 1) / 2 - 1]}`,
          }) : ''}
        </section>
      `)}

      ${hasStandaloneFaq ? html`
      <section id="faq">
        <h2><span class="num">${faqNum}</span>자주 묻는 질문</h2>
        ${faqItems}
      </section>
      ` : ''}

      ${sameBoardPosts.length > 0 ? html`
        <section id="same-board">
          <h2><span class="num">${sameBoardNum}</span>${board.title} 다른 안내</h2>
          <p>같은 분야 다른 지역 글도 함께 살펴보세요.</p>
          <ul class="related-list">
            ${sameBoardPosts.map(p => html`
              <li><a href="/${encodeURIComponent(board.slug)}/${encodeURIComponent(p.slug)}">
                <span class="related-region">${p.region}</span>
                <span class="related-title">${p.title}</span>
              </a></li>
            `)}
          </ul>
        </section>
      ` : ''}

      ${regionChips.length > 0 ? html`
        <section id="regions">
          <h2><span class="num">${regionsNum}</span>서비스 지역</h2>
          <p>${post.region} 인근 지역도 출장 상담 가능합니다.</p>
          <div class="region-list">
            ${regionChips.map(c => html`<a href="${c.href}">${c.name}</a>`)}
          </div>
        </section>
      ` : ''}

      ${relatedBoards.length > 0 ? html`
        <section id="related">
          <h2><span class="num">${relatedNum}</span>다른 안내 둘러보기</h2>
          <p>다른 분야 안내도 함께 살펴보세요.</p>
          <div class="region-list">
            ${relatedBoards.map(b => html`<a href="/${encodeURIComponent(b.slug)}">${b.title}</a>`)}
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
