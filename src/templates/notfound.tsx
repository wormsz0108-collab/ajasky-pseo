import { html } from 'hono/html';
import type { Site, Board } from '../types';
import { Layout } from './layout';

interface NotFoundProps {
  site: Site;
  boards: Pick<Board, 'slug' | 'title' | 'description'>[];
  attemptedPath?: string;
}

export function NotFoundPage(props: NotFoundProps) {
  const { site, boards, attemptedPath } = props;
  const phoneHref = `tel:${site.phone.replace(/-/g, '')}`;

  const inner = html`
    <main class="wrap-wide" style="text-align:center;padding:80px 20px 40px">
      <div style="font-size:96px;font-weight:900;color:var(--accent);letter-spacing:-.06em;line-height:1;margin-bottom:16px">404</div>
      <h1 style="font-size:24px;margin:0 0 12px;letter-spacing:-.02em">찾으시는 페이지가 없습니다</h1>
      <p style="color:var(--meta);margin:0 0 32px">${attemptedPath ? html`<code style="background:var(--bg-soft);padding:2px 8px;border-radius:6px">${attemptedPath}</code>` : ''}</p>

      <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-bottom:48px">
        <a class="btn primary" href="/">홈으로</a>
        <a class="btn outline" href="${phoneHref}">${site.phone}</a>
      </div>

      <div style="border-top:1px solid var(--line);padding-top:32px;text-align:left;max-width:760px;margin:0 auto">
        <h2 style="font-size:16px;margin:0 0 12px;color:var(--text-soft)">분야별 안내</h2>
        <div class="boards-grid">
          ${boards.map(b => html`
            <a class="board-tile" href="/${encodeURIComponent(b.slug)}">
              <span>${b.title}</span>
              ${b.description ? html`<small>${b.description}</small>` : ''}
            </a>
          `)}
        </div>
      </div>
    </main>
  `;

  return Layout({
    site, boards,
    title: `404 — ${site.site_name}`,
    description: '찾으시는 페이지가 없습니다.',
    canonicalPath: '/',
    ogType: 'website',
    children: inner,
  });
}
