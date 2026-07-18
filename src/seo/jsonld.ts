import type { Site, Board, Post } from '../types';
import { absoluteImageUrl } from '../lib/url';

function orgNode(site: Site) {
  const base = `https://${site.domain}`;
  return {
    '@type': 'LocalBusiness',
    '@id': `${base}/#org`,
    name: site.site_name,
    telephone: site.phone,
    url: `${base}/`,
    areaServed: '대한민국',
    logo: site.logo_url || undefined,
  };
}

function websiteNode(site: Site) {
  const base = `https://${site.domain}`;
  return {
    '@type': 'WebSite',
    '@id': `${base}/#website`,
    url: `${base}/`,
    name: site.site_name,
    inLanguage: 'ko',
    publisher: { '@id': `${base}/#org` },
  };
}

export function buildHomeJsonLd(site: Site) {
  return {
    '@context': 'https://schema.org',
    '@graph': [websiteNode(site), orgNode(site)],
  };
}

interface BuildBoardLdInput {
  site: Site;
  board: Pick<Board, 'slug' | 'title' | 'description'>;
  posts: { title: string; slug: string }[];
}

export function buildBoardJsonLd(input: BuildBoardLdInput) {
  const { site, board, posts } = input;
  const base = `https://${site.domain}`;
  const boardUrl = `${base}/${encodeURIComponent(board.slug)}`;
  return {
    '@context': 'https://schema.org',
    '@graph': [
      websiteNode(site),
      orgNode(site),
      {
        '@type': 'CollectionPage',
        '@id': `${boardUrl}#page`,
        url: boardUrl,
        name: board.title,
        description: board.description || `${site.site_name} ${board.title} 안내`,
        isPartOf: { '@id': `${base}/#website` },
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: '홈', item: `${base}/` },
          { '@type': 'ListItem', position: 2, name: board.title, item: boardUrl },
        ],
      },
      ...(posts.length > 0 ? [{
        '@type': 'ItemList',
        itemListElement: posts.slice(0, 50).map((p, idx) => ({
          '@type': 'ListItem',
          position: idx + 1,
          name: p.title,
          url: `${boardUrl}/${encodeURIComponent(p.slug)}`,
        })),
      }] : []),
    ],
  };
}

interface BuildArticleLdInput {
  site: Site;
  board: Pick<Board, 'slug' | 'title'>;
  post: Pick<Post,
    'title' | 'meta_description' | 'slug' |
    'published_at' | 'modified_at' | 'og_image_url'
  >;
  faq: { q: string; a: string }[];
  // 제원 비교표가 본문에 있는 글(=신규 발행분)에만 Speakable 을 부여한다.
  // 옛 글은 표·캡션이 없어 selector 가 비므로 아예 speakable 노드를 넣지 않는다.
  hasSpecTable?: boolean;
}

// GEO 강화 #2 — Speakable 지정 대상 회전 후보. 글별(slug 해시)로 하나 선택.
//   [0] 인트로 첫 문단(들)  #s1 = 첫 섹션 (markdown 파서가 anchor s1 부여)
//   [1] 첫 FAQ 답변         .faq 첫 항목의 답변
//   [2] 표 캡션             주입된 제원표의 <caption class="spec-caption">
const SPEAKABLE_SELECTORS: string[][] = [
  ['#s1 p'],
  ['.faq .faq-item:first-child .faq-a'],
  ['.spec-caption'],
];

function djb2(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h;
}

export function buildArticleJsonLd(input: BuildArticleLdInput) {
  const { site, board, post, faq, hasSpecTable } = input;
  const base = `https://${site.domain}`;
  const url = `${base}/${encodeURIComponent(board.slug)}/${encodeURIComponent(post.slug)}`;
  const img = absoluteImageUrl(post.og_image_url || site.og_image_url || `${base}/og-default.jpg`, site.domain);

  const articleNode: Record<string, unknown> = {
    '@type': 'Article',
    headline: post.title,
    description: post.meta_description,
    datePublished: post.published_at,
    dateModified: post.modified_at,
    image: img,
    mainEntityOfPage: url,
    author: { '@type': 'Organization', name: site.site_name },
    publisher: { '@id': `${base}/#org` },
  };

  // Speakable (GEO) — 신규 발행분(표 보유)에만. 글별 해시로 대상 1개 회전.
  if (hasSpecTable) {
    const sel = SPEAKABLE_SELECTORS[djb2(post.slug) % SPEAKABLE_SELECTORS.length];
    articleNode.speakable = { '@type': 'SpeakableSpecification', cssSelector: sel };
  }

  const graph: object[] = [
    websiteNode(site),
    orgNode(site),
    articleNode,
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: '홈', item: `${base}/` },
        { '@type': 'ListItem', position: 2, name: board.title, item: `${base}/${encodeURIComponent(board.slug)}` },
        { '@type': 'ListItem', position: 3, name: post.title, item: url },
      ],
    },
  ];

  if (faq.length > 0) {
    graph.push({
      '@type': 'FAQPage',
      mainEntity: faq.map(f => ({
        '@type': 'Question',
        name: f.q,
        acceptedAnswer: { '@type': 'Answer', text: f.a },
      })),
    });
  }

  return { '@context': 'https://schema.org', '@graph': graph };
}
