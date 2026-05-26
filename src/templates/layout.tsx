import { html } from 'hono/html';
import type { Site, Board } from '../types';
import { STYLES } from './styles';

interface LayoutProps {
  site: Site;
  boards: Pick<Board, 'slug' | 'title'>[];
  title: string;
  description: string;
  canonicalPath: string;
  ogImageUrl?: string | null;
  ogType?: 'website' | 'article';
  activeBoardSlug?: string | null;
  keywords?: string;
  jsonLd?: object | null;
  noindex?: boolean;
  children?: any;
}

const PhoneIcon = () => html`
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.86 19.86 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.86 19.86 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>
  </svg>
`;

export function Layout(props: LayoutProps) {
  const {
    site, boards, title, description, canonicalPath,
    ogImageUrl, ogType = 'website', activeBoardSlug, keywords, jsonLd, noindex, children,
  } = props;

  const fullUrl = `https://${site.domain}${canonicalPath}`;
  const ogImg = ogImageUrl || site.og_image_url || `https://${site.domain}/og-default.jpg`;
  const phoneHref = `tel:${site.phone.replace(/-/g, '')}`;

  return html`<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<meta name="description" content="${description}">
${keywords ? html`<meta name="keywords" content="${keywords}">` : ''}
${noindex ? html`<meta name="robots" content="noindex,follow,noarchive,nosnippet">
<meta name="Yeti" content="noindex,follow,noarchive,nosnippet">
<meta name="googlebot" content="noindex,follow,noarchive,nosnippet">` : ''}
<link rel="canonical" href="${fullUrl}">

<meta property="og:type" content="${ogType}">
<meta property="og:site_name" content="${site.site_name}">
<meta property="og:title" content="${title}">
<meta property="og:description" content="${description}">
<meta property="og:url" content="${fullUrl}">
<meta property="og:image" content="${ogImg}">
<meta property="og:image:width" content="1080">
<meta property="og:image:height" content="1080">
<meta property="og:image:alt" content="${title}">
<meta property="og:locale" content="ko_KR">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${title}">
<meta name="twitter:description" content="${description}">
<meta name="twitter:image" content="${ogImg}">

<meta name="thumbnail" content="${ogImg}">
${site.naver_verification ? html`<meta name="naver-site-verification" content="${site.naver_verification}">` : ''}
${site.google_verification ? html`<meta name="google-site-verification" content="${site.google_verification}">` : ''}

<link rel="alternate" type="application/rss+xml" title="${site.site_name} RSS" href="https://${site.domain}/rss.xml">

<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">

<style>${STYLES}</style>

${jsonLd ? html`<script type="application/ld+json">${JSON.stringify(jsonLd)}</script>` : ''}
</head>
<body>

<header class="top">
  <div class="top-inner">
    <a class="logo" href="/"><span class="dot"></span>${site.site_name}</a>
    <nav class="nav">
      ${boards.map(b => html`
        <a href="/${encodeURIComponent(b.slug)}" class="${activeBoardSlug === b.slug ? 'on' : ''}">${b.title}</a>
      `)}
    </nav>
    <a class="top-cta" href="${phoneHref}">
      ${PhoneIcon()}
      ${site.phone}
    </a>
  </div>
</header>

${children}

<footer>
  <div class="f-inner">
    <div>
      <h4>연락</h4>
      <p><a href="${phoneHref}">${site.phone}</a></p>
    </div>
    <div>
      <h4>안내</h4>
      <p>현장 사진을 보내주시면 정확한 견적이 빠릅니다.<br>24시 전국 출장 가능.</p>
    </div>
  </div>
</footer>

</body>
</html>`;
}
