import type { Site, Board, Post } from '../types';

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
}

export function buildArticleJsonLd(input: BuildArticleLdInput) {
  const { site, board, post, faq } = input;
  const base = `https://${site.domain}`;
  const url = `${base}/${encodeURIComponent(board.slug)}/${encodeURIComponent(post.slug)}`;
  const img = post.og_image_url || site.og_image_url || `${base}/og-default.jpg`;

  const graph: object[] = [
    websiteNode(site),
    orgNode(site),
    {
      '@type': 'Article',
      headline: post.title,
      description: post.meta_description,
      datePublished: post.published_at,
      dateModified: post.modified_at,
      image: img,
      mainEntityOfPage: url,
      author: { '@type': 'Organization', name: site.site_name },
      publisher: { '@id': `${base}/#org` },
    },
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
