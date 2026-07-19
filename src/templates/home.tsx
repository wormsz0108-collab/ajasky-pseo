import { html } from 'hono/html';
import type { Site, Board } from '../types';
import { Layout } from './layout';
import { Thumbnail } from './thumbnail';
import type { ThumbnailText } from '../lib/thumbnail-text';
import { QUOTE_GUIDE_URL_PATH } from '../lib/routes';

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
  const priceFocused = site.domain === 'wormsz1.store';
  const homeTitle = priceFocused
    ? `${site.site_name} | 스카이차 비용·가격·요금 견적 안내`
    : `${site.site_name} | 전국 스카이차·고소작업차 배차 안내`;
  const homeHeading = priceFocused
    ? '스카이차 비용·가격·요금 안내'
    : '전국 스카이차 현장·배차 안내';
  const homeDescription = priceFocused
    ? `${site.site_name}의 스카이차 비용·가격·요금과 현장별 견적 기준 안내. 높이·반경·진입 조건을 확인하고 24시 상담하세요.`
    : `${site.site_name}의 수도권·전국 스카이차 현장·배차 안내. 지역별 고소작업차량 정보와 견적 준비 기준을 확인하세요.`;

  const inner = html`
    <main class="wrap-wide">

      <div class="page-h" style="margin-top:24px">
        <h1>${homeHeading}</h1>
        <p class="desc">${homeDescription}</p>
        <p style="margin-top:14px">
          <a class="btn primary" href="${phoneHref}">전화 상담 ${site.phone}</a>
        </p>
      </div>

      <div class="home-guide">
        <div><strong>비용이 달라지는 현장 조건을 먼저 확인하세요</strong><span>높이·수평 반경·진입로·통제·작업 시간을 상담 문장으로 정리할 수 있습니다.</span></div>
        <a class="btn outline" href="${QUOTE_GUIDE_URL_PATH}">견적 준비 가이드</a>
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
    title: homeTitle,
    description: homeDescription,
    canonicalPath: '/',
    ogType: 'website',
    keywords: `${site.site_name},스카이차,스카이차 비용,스카이차 일대,고소작업차량,스카이차 가격,스카이차 요금,스카이차 이용료,스카이 작업차,${site.phone}`,
    jsonLd,
    noindex: false, // 홈 색인 허용 — 브랜드 검색 노출 위해 해제 (사장님 2026-07-15 지시)
    children: inner,
  });
}
