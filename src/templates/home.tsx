import { html } from 'hono/html';
import type { Site, Board } from '../types';
import { Layout } from './layout';
import { Thumbnail } from './thumbnail';
import type { ThumbnailText } from '../lib/thumbnail-text';

interface HomeRecentPost {
  board_slug: string;
  board_title: string;
  slug: string;
  title: string;
  region: string;
  published_at: string;
  og_image_url: string | null;
  thumbnailText: ThumbnailText;
}

interface HomePageProps {
  site: Site;
  boards: Pick<Board, 'slug' | 'title' | 'description'>[];
  recentPosts: HomeRecentPost[];
  jsonLd?: object | null;
}

export function HomePage(props: HomePageProps) {
  const { site, boards, recentPosts, jsonLd } = props;
  const phoneHref = `tel:${site.phone.replace(/-/g, '')}`;

  const inner = html`
    <main class="wrap-wide">

      <div class="page-h" style="margin-top:24px">
        <h1>${site.site_name} — 스카이차 / 고소작업차량</h1>
        <p class="desc">현장 사진 한 장이면 정확한 견적이 가능합니다. 24시 전국 배차 / 안전 책임 작업.</p>
        <p style="margin-top:14px">
          <a class="btn primary" href="${phoneHref}">전화 상담 ${site.phone}</a>
        </p>
      </div>

      <div class="section-h">
        <h2>분야별 안내</h2>
      </div>
      <div class="boards-grid">
        ${boards.map(b => html`
          <a class="board-tile" href="/${encodeURIComponent(b.slug)}">
            <span>${b.title}</span>
            ${b.description ? html`<small>${b.description}</small>` : ''}
          </a>
        `)}
      </div>

      <div class="section-h">
        <h2>최근 안내</h2>
        ${recentPosts.length > 0 ? html`<a href="/${encodeURIComponent(boards[0]?.slug || '')}">전체 보기 →</a>` : ''}
      </div>
      ${recentPosts.length === 0 ? html`
        <p style="color:var(--meta);padding:40px 0">곧 콘텐츠가 추가됩니다.</p>
      ` : html`
        <div class="grid">
          ${recentPosts.map(p => html`
            <a class="card" href="/${encodeURIComponent(p.board_slug)}/${encodeURIComponent(p.slug)}">
              <div class="thumb">
                ${Thumbnail({
                  imageUrl: p.og_image_url || '/media/photos/001.jpg',
                  ribbon: p.thumbnailText.ribbon,
                  headlinePrefix: p.thumbnailText.headlinePrefix,
                  headlineHighlight: p.thumbnailText.headlineHighlight,
                  brandName: site.site_name,
                  phone: site.phone,
                  alt: `${p.region} ${p.board_title}`,
                })}
              </div>
              <div class="body">
                <p class="ttl">${p.title}</p>
                <p class="mt"><span>${p.board_title}</span><span>·</span><span>${p.region}</span></p>
              </div>
            </a>
          `)}
        </div>
      `}

    </main>
  `;

  return Layout({
    site, boards,
    title: `${site.site_name} | 스카이차·고소작업차량 안내`,
    description: `${site.site_name}는 수도권·전국 스카이차 일대·고소작업차량 안내를 제공합니다. 24시 전국 배차 / 안전 책임 작업.`,
    canonicalPath: '/',
    ogType: 'website',
    keywords: `${site.site_name},스카이차,스카이차 비용,스카이차 일대,고소작업차량,스카이차 가격,스카이차 요금,스카이차 이용료,스카이 작업차,${site.phone}`,
    jsonLd,
    noindex: true,  // 홈도 검색 노출 제외 — 글(알맹이)만 색인 (사장님 방침)
    children: inner,
  });
}
