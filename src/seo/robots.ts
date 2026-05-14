import type { Site } from '../types';

// 한국 검색엔진 봇 명시적 허용 + 영문 검색엔진도 허용
// Yeti = 네이버, Daumoa = 다음, NaverBot = 구버전 네이버
export function renderRobots(site: Site): string {
  return `User-agent: Yeti
Allow: /
Disallow: /api/
Disallow: /_health
Crawl-delay: 1

User-agent: NaverBot
Allow: /
Disallow: /api/
Disallow: /_health
Crawl-delay: 1

User-agent: Daumoa
Allow: /
Disallow: /api/
Disallow: /_health
Crawl-delay: 1

User-agent: Googlebot
Allow: /
Disallow: /api/
Disallow: /_health

User-agent: bingbot
Allow: /
Disallow: /api/
Disallow: /_health

User-agent: *
Allow: /
Disallow: /api/
Disallow: /_health

Sitemap: https://${site.domain}/sitemap.xml
`;
}
