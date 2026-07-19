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

export function buildGuideJsonLd(site: Site, faq: { q: string; a: string }[]) {
  const base = `https://${site.domain}`;
  const path = `/${encodeURIComponent('스카이차-견적-가이드')}`;
  const url = `${base}${path}`;
  const nationwide = site.domain === 'ajasky.co.kr';
  const name = nationwide
    ? '전국 스카이차 비용·가격·요금 현장 견적 준비 가이드'
    : '스카이차 비용·가격·요금 현장 견적 준비 가이드';

  return {
    '@context': 'https://schema.org',
    '@graph': [
      websiteNode(site),
      orgNode(site),
      {
        '@type': 'WebPage',
        '@id': `${url}#page`,
        url,
        name,
        description: '현장 주소, 높이, 수평 반경, 진입 조건, 작업 내용과 일정을 정리해 스카이차 견적 상담을 준비하는 방법입니다.',
        inLanguage: 'ko-KR',
        isPartOf: { '@id': `${base}/#website` },
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: '홈', item: `${base}/` },
          { '@type': 'ListItem', position: 2, name: '스카이차 견적 준비 가이드', item: url },
        ],
      },
      {
        '@type': 'HowTo',
        name: '스카이차 견적 상담 준비 방법',
        description: '현장 조건을 정리해 스카이차 상담을 준비하는 순서입니다.',
        step: [
          { '@type': 'HowToStep', position: 1, name: '주소와 높이 확인', text: '정확한 현장 주소와 건물 층수 또는 작업 높이를 확인합니다.' },
          { '@type': 'HowToStep', position: 2, name: '진입 조건 촬영', text: '진입로와 차량 설치 공간, 작업 지점이 보이도록 사진을 준비합니다.' },
          { '@type': 'HowToStep', position: 3, name: '작업량 정리', text: '작업 종류와 예상 작업량, 소요 시간을 정리합니다.' },
          { '@type': 'HowToStep', position: 4, name: '일정 전달', text: '희망 날짜와 시작 시간, 통제 가능 여부를 전달합니다.' },
        ],
      },
      {
        '@type': 'FAQPage',
        mainEntity: faq.map(f => ({
          '@type': 'Question',
          name: f.q,
          acceptedAnswer: { '@type': 'Answer', text: f.a },
        })),
      },
    ],
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
