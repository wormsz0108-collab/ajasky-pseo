import { html } from 'hono/html';
import type { Site, Board, Post } from '../types';
import { Layout } from './layout';
import { Thumbnail } from './thumbnail';
import type { ThumbnailText } from '../lib/thumbnail-text';

interface PostCardData {
  title: string;
  slug: string;
  region: string;
  published_at: string;
  og_image_url: string | null;
  thumbnailText: ThumbnailText;
}

interface BoardPageProps {
  site: Site;
  boards: Pick<Board, 'slug' | 'title'>[];
  board: Pick<Board, 'slug' | 'title' | 'description'>;
  posts: PostCardData[];
  page: number;
  totalPages: number;
  jsonLd?: object | null;
}

export function BoardPage(props: BoardPageProps) {
  const { site, boards, board, posts, page, totalPages, jsonLd } = props;
  const canonicalPath = `/${encodeURIComponent(board.slug)}${page > 1 ? `?page=${page}` : ''}`;

  const inner = html`
    <main class="wrap-wide">
      <nav class="breadcrumb">
        <a href="/">홈</a><span class="sep">›</span>
        <span>${board.title}</span>
      </nav>

      <div class="page-h">
        <h1>${board.title}</h1>
        ${board.description ? html`<p class="desc">${board.description}</p>` : html`<p class="desc">${board.title} 관련 지역별 안내 글 모음</p>`}
      </div>

      ${posts.length === 0 ? html`
        <p style="color:var(--meta);padding:40px 0">아직 등록된 글이 없습니다.</p>
      ` : html`
        <div class="grid">
          ${posts.map(p => html`
            <a class="card" href="/${encodeURIComponent(board.slug)}/${encodeURIComponent(p.slug)}">
              <div class="thumb">
                ${Thumbnail({
                  imageUrl: p.og_image_url || '/media/default-hero.jpg',
                  ribbon: p.thumbnailText.ribbon,
                  headlinePrefix: p.thumbnailText.headlinePrefix,
                  headlineHighlight: p.thumbnailText.headlineHighlight,
                  brandName: site.site_name,
                  phone: site.phone,
                  alt: `${p.region} ${board.title}`,
                })}
              </div>
              <div class="body">
                <p class="ttl">${p.title}</p>
                <p class="mt"><span>${formatDate(p.published_at)}</span><span>·</span><span>${p.region}</span></p>
              </div>
            </a>
          `)}
        </div>

        ${totalPages > 1 ? html`
          <nav class="pag">
            ${page > 1 ? html`<a href="/${encodeURIComponent(board.slug)}?page=${page - 1}">이전</a>` : ''}
            ${range(1, totalPages).map(n => n === page
              ? html`<span class="now">${n}</span>`
              : html`<a href="/${encodeURIComponent(board.slug)}?page=${n}">${n}</a>`
            )}
            ${page < totalPages ? html`<a href="/${encodeURIComponent(board.slug)}?page=${page + 1}">다음</a>` : ''}
          </nav>
        ` : ''}
      `}
    </main>
  `;

  return Layout({
    site, boards,
    title: `${board.title} | ${site.site_name}`,
    description: board.description || `${site.site_name} ${board.title} 안내 모음`,
    canonicalPath,
    ogType: 'website',
    activeBoardSlug: board.slug,
    keywords: `${board.title},${site.site_name},${board.title} 안내,${board.title} 비교`,
    jsonLd,
    children: inner,
  });
}

function formatDate(iso: string) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`;
}

function range(from: number, to: number) {
  return Array.from({ length: to - from + 1 }, (_, i) => from + i);
}
