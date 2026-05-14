# CLAUDE.md — 아자스카이 프로그래매틱 SEO 시스템

> Claude Code 핸드오프 문서. sfskycar.com(uniz.ai 플랫폼)과 동일한 구조의 프로그래매틱 SEO 사이트를, 사장님의 기존 Cloudflare 스택 위에 자체 구축한다.

---

## 0. 작업 목표

- 4만~9만 개 longtail 페이지를 **DB row 단위**로 관리
- 1개 Worker가 `Host` 헤더로 사이트를 분기 → SSR 렌더링
- 기존 Python(Selenium + Gemini) 파이프라인은 **그대로 재사용**
- 기존 40개 region-specific 도메인 **유지**, 그러나 한 Worker에 통합

**이전 방식의 한계:**
HTML 파일 4만 개 → git push → Cloudflare 빌드 → Netlify overage (사장님 메모리 참조)

**바뀐 방식:**
INSERT 1번 → 즉시 반영. 빌드 0.

---

## 1. 핵심 아키텍처

```
[Python 자동화 파이프라인 (기존)]
  Selenium + Gemini API → 9-섹션 글 생성 (JSON)
        ↓ HTTPS POST /api/posts (Bearer token)
[Cloudflare Worker (Hono) + D1]
  - REST API: 글 INSERT/UPDATE/DELETE
  - SSR 라우터: 글 조회 → HTML 렌더
  - sitemap.xml 동적 생성 (1,000 URL씩 분할)
  - JSON-LD / OG / canonical 자동 삽입
        ↓
[사용자 브라우저 / 네이버 / 구글 크롤러]
```

---

## 2. 기술 스택

| 레이어 | 사용 기술 | 비용 |
|---|---|---|
| 라우팅/SSR | Cloudflare Workers + Hono | 100k req/일 무료, 이후 $5/월 |
| DB | Cloudflare D1 (SQLite) | 5GB / 25M read/일 무료 |
| 이미지 | Cloudflare R2 | 10GB 무료 |
| 콘텐츠 생성 | Python + Gemini (기존) | API 사용량만 |
| 도메인 | 기존 40개 그대로 | - |

**왜 Next.js 안 쓰나?**
- sfskycar는 Next.js + AWS EC2지만, **출력 HTML은 동일**하다.
- Hono on Workers가 Cloudflare에서 훨씬 저렴하고 단순.
- Programmatic SEO에는 클라이언트 인터랙티비티가 필요 없음 (SSR만 필요).
- React 의존성 0 = 빌드 0초 = Netlify 같은 overage 사고 발생 불가.

---

## 3. 디렉터리 구조

```
ajasky-pseo/
├── CLAUDE.md                    # 이 파일
├── wrangler.toml                # Worker 설정 (D1/R2 binding)
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts                 # Worker entry (Hono 라우터)
│   ├── routes/
│   │   ├── home.ts              # /
│   │   ├── board.ts             # /{board_slug}
│   │   ├── post.ts              # /{board_slug}/{post_slug}
│   │   ├── sitemap.ts           # sitemap.xml + 분할
│   │   ├── robots.ts            # robots.txt
│   │   └── api.ts               # /api/posts (Python에서 호출)
│   ├── templates/
│   │   ├── layout.tsx           # 공통 레이아웃 (헤더/푸터/메타)
│   │   ├── post-template.tsx    # 9-섹션 글 템플릿
│   │   ├── board-template.tsx   # 게시판(목록) 템플릿
│   │   └── home-template.tsx
│   ├── db/
│   │   ├── schema.sql           # D1 스키마
│   │   ├── seed.sql             # 초기 sites + 8개 boards
│   │   └── queries.ts           # 쿼리 헬퍼
│   ├── seo/
│   │   ├── jsonld.ts            # JSON-LD 생성 (WebSite/Organization/Article/Breadcrumb/FAQ)
│   │   └── meta.ts              # meta 태그 생성
│   └── lib/
│       ├── auth.ts              # Bearer token 검증
│       └── slug.ts              # 한글 → URL slug 변환
├── content-pipeline/             # Python 파이프라인 (기존 코드 이전)
│   ├── generate.py              # Gemini로 글 생성 (9-섹션)
│   ├── publish.py               # Worker API에 POST
│   ├── prompt-template.txt      # 9-섹션 시스템 프롬프트
│   ├── regions.py               # 지역명 데이터 (광역/시군구/법정동)
│   └── longtails.py             # longtail 템플릿 풀
└── README.md
```

---

## 4. 데이터 모델 (D1)

### `sites` — 멀티 도메인
```sql
CREATE TABLE sites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  domain TEXT UNIQUE NOT NULL,        -- 예: ajasky.kr, 01092490510.com
  site_name TEXT NOT NULL,            -- 예: "아자스카이"
  phone TEXT NOT NULL DEFAULT '010-9249-0510',
  logo_url TEXT,
  og_image_url TEXT,
  naver_verification TEXT,            -- 네이버 사이트 인증 코드
  google_verification TEXT,
  cafe_url TEXT DEFAULT 'https://cafe.naver.com/ajasky',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `boards` — 게시판(카테고리)
```sql
CREATE TABLE boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES sites(id),
  slug TEXT NOT NULL,                 -- "스카이차-일대"
  title TEXT NOT NULL,                -- "스카이차 일대"
  description TEXT,
  display_order INTEGER DEFAULT 0,
  parent_board_id INTEGER REFERENCES boards(id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(site_id, slug)
);
CREATE INDEX idx_boards_site ON boards(site_id);
```

### `posts` — 개별 글
```sql
CREATE TABLE posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site_id INTEGER NOT NULL REFERENCES sites(id),
  board_id INTEGER NOT NULL REFERENCES boards(id),
  slug TEXT NOT NULL,                 -- "전북-스카이차-일대-비용-절감"
  title TEXT NOT NULL,
  region TEXT NOT NULL,               -- "전북" / "청운동"
  region_type TEXT,                   -- "광역" / "시군구" / "법정동"
  meta_description TEXT NOT NULL,
  meta_keywords TEXT NOT NULL,
  body_md TEXT NOT NULL,              -- 본문(Markdown)
  toc_json TEXT,                      -- 목차 JSON
  faq_json TEXT,                      -- FAQ JSON
  og_image_url TEXT,
  status TEXT DEFAULT 'published',    -- published / draft
  published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(site_id, slug)
);
CREATE INDEX idx_posts_site_board ON posts(site_id, board_id);
CREATE INDEX idx_posts_published ON posts(published_at DESC);
CREATE INDEX idx_posts_region ON posts(site_id, region);
```

### 시드 데이터: 8개 보드 (sfskycar 구조 그대로)
```sql
INSERT INTO sites (domain, site_name, phone) VALUES
  ('ajasky.kr', '아자스카이', '010-9249-0510');

INSERT INTO boards (site_id, slug, title, display_order) VALUES
  (1, '스카이차',         '스카이차',         1),
  (1, '스카이차-일대',     '스카이차 일대',     2),
  (1, '스카이-작업차',     '스카이 작업차',     3),
  (1, '스카이차-요금',     '스카이차 요금',     4),
  (1, '스카이차-비용',     '스카이차 비용',     5),
  (1, '스카이차-가격',     '스카이차 가격',     6),
  (1, '스카이차-이용료',   '스카이차 이용료',   7),
  (1, '고소작업차량',      '고소작업차량',      8);
```

---

## 5. URL 라우팅

| URL | 설명 | 데이터 |
|---|---|---|
| `/` | 사이트 홈 | sites + 최신 글 12개 |
| `/{board_slug}` | 보드 목록(20개씩 페이지네이션) | `boards.slug` 매칭 |
| `/{board_slug}?page=2` | 보드 목록 N페이지 | |
| `/{board_slug}/{post_slug}` | 개별 글 | `posts.slug` 매칭 |
| `/sitemap.xml` | sitemap 인덱스 | 동적 |
| `/sitemap-pages-1.xml` | 정적 페이지 | - |
| `/sitemap-boards-1.xml` | 보드 페이지 | boards |
| `/sitemap-posts-N.xml` | 글 (1,000개씩 분할) | LIMIT 1000 OFFSET (N-1)*1000 |
| `/robots.txt` | robots.txt | - |
| `POST /api/posts` | 글 등록 (Bearer token) | - |
| `PUT /api/posts/:id` | 글 수정 | - |
| `DELETE /api/posts/:id` | 글 삭제 | - |

### Host 헤더로 사이트 분기 (멀티 도메인 핵심)
```typescript
// src/index.ts
import { Hono } from 'hono';

const app = new Hono<{ Bindings: Env, Variables: { site: Site } }>();

app.use('*', async (c, next) => {
  const host = c.req.header('host');
  const site = await c.env.DB.prepare(
    'SELECT * FROM sites WHERE domain = ?'
  ).bind(host).first<Site>();
  if (!site) return c.text('Site not found', 404);
  c.set('site', site);
  await next();
});

app.get('/', homeRoute);
app.get('/sitemap.xml', sitemapIndex);
app.get('/sitemap-:type-:n.xml', sitemapPart);
app.get('/robots.txt', robotsRoute);
app.route('/api', apiRoutes);
app.get('/:boardSlug', boardRoute);
app.get('/:boardSlug/:postSlug', postRoute);

export default app;
```

### `wrangler.toml` 예시
```toml
name = "ajasky-pseo"
main = "src/index.ts"
compatibility_date = "2026-05-01"

[[d1_databases]]
binding = "DB"
database_name = "ajasky-pseo-db"
database_id = "<wrangler d1 create 결과로 받는 ID>"

[[r2_buckets]]
binding = "MEDIA"
bucket_name = "ajasky-media"

[vars]
WORKER_API_TOKEN_HASH = "<sha256 of token>"

# 멀티 도메인 라우팅 - 40개 도메인을 같은 Worker에 연결
routes = [
  { pattern = "ajasky.kr/*", custom_domain = true },
  { pattern = "01092490510.com/*", custom_domain = true },
  # ... 38개 더
]
```

---

## 6. 9-섹션 글 템플릿 (sfskycar 분석 기반)

### 6.1 Gemini 시스템 프롬프트
```
역할: 한국어 SEO 블로그 작가
목표: {지역} {보드 키워드} 안내 글을 9-섹션 구조로 작성

엄수 규칙:
1. "렌탈" 단어 사용 절대 금지 ("일대", "이용", "사용"으로 대체)
2. 가격/비용/시간 같은 구체 수치는 단언 금지 ("달라질 수 있습니다", "~인 편이 좋습니다")
3. 지역명은 도입과 각 h2 섹션 첫 문장에 자연스럽게 삽입
4. h1 정확히 1개, h2 정확히 8개, h3 정확히 4개 유지
5. 각 h2 섹션 본문은 200~350자
6. 리스트 항목은 정확히 4~5개
7. 이전 글과 동일한 문장 재사용 금지

구조:
[h1] {지역} {키워드} {longtail 문장}
[목차 (Table of contents)]

[h2] 1. {지역} {키워드}                  ← 도입, 200~350자
[h2] 2. {지역} 스카이차 선택
  [h3] 확인할 점                         ← 번호 리스트 4개
[h2] 3. {지역} 현장 체크
  [h3] 체크리스트                        ← 불릿 5개
[h2] 4. 진행 절차
  [h3] 작업 흐름                         ← 단계 5개
[h2] 5. 비용 기준
  [h3] 비용 결정 요소                    ← 불릿 5개
[h2] 6. 주의할 점
  [h3] 실수 줄이기                       ← 불릿 5개
[h2] 7. 상담 팁                          ← 200~300자
[h2] 8. 자주 묻는 질문(FAQ)              ← Q&A 4쌍
[h2] 9. 서비스 지역                      ← 인근 시군구 5~7개

출력 형식: JSON
{
  "title": "...",
  "meta_description": "...(120자 이내)",
  "meta_keywords": "{지역} {키워드},{키워드}",
  "body_md": "## 1. ...\n\n...",
  "toc": [{"level":1,"title":"..."}, ...],
  "faq": [{"q":"...","a":"..."},...]
}
```

### 6.2 변수 풀
```python
# content-pipeline/regions.py
REGIONS = {
    "광역": [
        "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
        "경기도", "강원특별자치도", "충북", "충남",
        "전북특별자치도", "전남", "경북", "경남", "제주특별자치도"
    ],
    "시군구": [...],   # 사장님 보유 경기/인천 데이터
    "법정동": [...]    # 사장님 보유 90k 키워드
}

# content-pipeline/longtails.py
# 보드별로 다른 longtail 풀 (sfskycar 분석에서 추출)
LONGTAILS_BY_BOARD = {
    "스카이차-일대": [
        "비용 절감에 도움이 되는 선택",
        "이동형 장비 활용이 필요한 순간",
        "작업 전 확인해야 할 안전 포인트",
        "현장 여건에 맞춘 진행 방식",
        "작업 효율을 높이는 준비",
        "이용 전 점검해야 할 항목",
        # ... 사장님 PowerLink 키워드에서 추가
    ],
    "스카이차-비용": [
        "현장 사진을 어디서 어떻게 찍어야 할까",
        "현장 변수가 많을수록 체크해야 할 것",
        "협소 골목 현장은 왜 비용 편차가 클까",
        "옥상 난간이 높은 건물은 접근이 달라질까",
        "야간 작업은 왜 달라질 수 있을까",
        "건물 층수만으로는 부족한 이유",
        # ...
    ],
    # 8개 보드 모두 별도 풀
}
```

### 6.3 한 글당 unique 키 = `(site, region, board, longtail)`

---

## 7. SEO 필수 구현

### 7.1 메타 태그 (모든 페이지 공통)
```html
<title>{글 제목}</title>
<meta name="description" content="{meta_description}">
<meta name="keywords" content="{meta_keywords}">
<meta name="naver-site-verification" content="{site.naver_verification}">
<link rel="canonical" href="{full_url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{og_image_url}">
<meta property="og:url" content="{full_url}">
<meta name="twitter:card" content="summary_large_image">
```

### 7.2 JSON-LD (개별 글 페이지) — sfskycar 패턴 그대로
```typescript
// src/seo/jsonld.ts
export function buildJsonLd(site, board, post, faq) {
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": `https://${site.domain}/#website`,
        "url": `https://${site.domain}/`,
        "name": site.site_name,
        "inLanguage": "ko"
      },
      {
        "@type": "Organization",
        "@id": `https://${site.domain}/#organization`,
        "name": site.site_name,
        "logo": { "@type": "ImageObject", "url": site.logo_url },
        "telephone": site.phone
      },
      {
        "@type": "Article",
        "headline": post.title,
        "description": post.meta_description,
        "datePublished": post.published_at,
        "dateModified": post.modified_at,
        "image": post.og_image_url,
        "author": { "@type": "Organization", "name": site.site_name }
      },
      {
        "@type": "BreadcrumbList",
        "itemListElement": [
          { "@type": "ListItem", "position": 1, "name": "홈", "item": `https://${site.domain}/` },
          { "@type": "ListItem", "position": 2, "name": board.title, "item": `https://${site.domain}/${board.slug}` },
          { "@type": "ListItem", "position": 3, "name": post.title }
        ]
      },
      faq && {
        "@type": "FAQPage",
        "mainEntity": faq.map(({q, a}) => ({
          "@type": "Question",
          "name": q,
          "acceptedAnswer": { "@type": "Answer", "text": a }
        }))
      }
    ].filter(Boolean)
  };
}
```

### 7.3 sitemap 분할 전략
```typescript
// src/routes/sitemap.ts
const POSTS_PER_SITEMAP = 1000;

// /sitemap.xml — 인덱스
app.get('/sitemap.xml', async (c) => {
  const site = c.get('site');
  const { count } = await c.env.DB.prepare(
    'SELECT COUNT(*) as count FROM posts WHERE site_id = ? AND status = "published"'
  ).bind(site.id).first<{count: number}>();
  const numPostSitemaps = Math.ceil(count / POSTS_PER_SITEMAP);

  const sitemaps = [
    { loc: `https://${site.domain}/sitemap-pages-1.xml`, lastmod: '...' },
    { loc: `https://${site.domain}/sitemap-boards-1.xml`, lastmod: '...' },
    ...Array.from({length: numPostSitemaps}, (_, i) => ({
      loc: `https://${site.domain}/sitemap-posts-${i+1}.xml`,
      lastmod: '...'
    }))
  ];
  return c.text(buildSitemapIndex(sitemaps), 200, { 'content-type': 'application/xml' });
});

// /sitemap-posts-N.xml — 1,000개씩
app.get('/sitemap-posts-:n{[0-9]+}.xml', async (c) => {
  const site = c.get('site');
  const n = parseInt(c.req.param('n'));
  const offset = (n - 1) * POSTS_PER_SITEMAP;
  const posts = await c.env.DB.prepare(
    `SELECT p.slug, p.modified_at, b.slug as board_slug
     FROM posts p JOIN boards b ON p.board_id = b.id
     WHERE p.site_id = ? AND p.status = "published"
     ORDER BY p.id LIMIT ? OFFSET ?`
  ).bind(site.id, POSTS_PER_SITEMAP, offset).all();
  return c.text(buildPostSitemap(posts.results, site.domain), 200, { 'content-type': 'application/xml' });
});
```

### 7.4 robots.txt
```
User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Sitemap: https://{site.domain}/sitemap.xml
```

---

## 8. Python ↔ Worker 연동 API

### 8.1 글 등록
```
POST https://ajasky.kr/api/posts
Authorization: Bearer {WORKER_API_TOKEN}
Content-Type: application/json

{
  "site_domain": "ajasky.kr",
  "board_slug": "스카이차-일대",
  "slug": "전북-스카이차-일대-비용-절감",
  "title": "전북 스카이차 일대 비용 절감에 도움이 되는 선택",
  "region": "전북",
  "region_type": "광역",
  "meta_description": "전북 스카이차 일대는 작업 환경에 맞춘 장비 검토가 중요하다는 점을 짚어드립니다.",
  "meta_keywords": "전북 스카이차 일대,스카이차 일대",
  "body_md": "## 1. 전북 스카이차 일대\n\n전북 스카이차 일대에서 작업을...",
  "toc_json": "[{\"level\":1,\"title\":\"전북 스카이차 일대\"}, ...]",
  "faq_json": "[{\"q\":\"...\",\"a\":\"...\"}, ...]",
  "og_image_url": "https://media.ajasky.kr/og-default.jpg"
}

→ 201 { "id": 12345, "url": "https://ajasky.kr/스카이차-일대/전북-..." }
→ 409 { "error": "duplicate_slug" }   (같은 site에 같은 slug 존재)
→ 401 { "error": "unauthorized" }
```

### 8.2 중복 정책
- `posts.slug`는 `(site_id, slug)` UNIQUE
- 같은 slug 재요청 → 기본 409
- `?force=1` 시 UPDATE
- 같은 (region, board) 조합 발행 전 확인 — 30일 쿨다운 권장

### 8.3 Python 측 publish.py 골격
```python
# content-pipeline/publish.py
import os, time, random, requests

WORKER_API = os.environ.get("WORKER_API", "https://ajasky.kr/api/posts")
TOKEN = os.environ["WORKER_API_TOKEN"]

def publish(post_data: dict, retries=3):
    for attempt in range(retries):
        try:
            r = requests.post(
                WORKER_API,
                json=post_data,
                headers={"Authorization": f"Bearer {TOKEN}"},
                timeout=30,
            )
            if r.status_code == 409:
                print(f"[skip] duplicate: {post_data['slug']}")
                return None
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt + random.random())
```

---

## 9. 발행 정책 (네이버 안전 모드 — 사장님 기존 정책 유지)

| 항목 | 정책 |
|---|---|
| 일 발행 한도 | 사이트당 **1~2개/일** (네이버 페널티 회피) |
| 발행 시간 | 랜덤 간격 (사장님 기존 cron 그대로) |
| 보드별 분산 | 동일 보드에 연속 발행 X |
| 동일 (region, board) 재발행 | 최소 30일 간격 |
| 글 수정 | 발행 후 7일 뒤부터 가능 |
| OG 이미지 | 보드별 1장 = 8장 정도로 다양화 (sfskycar는 1장만 — 너무 균일하면 위험) |
| 횡 미러링 | 사용 금지 (사장님 기존 정책) |
| 원본 이미지 | 수정 금지, 메모리 버퍼만 (사장님 기존 정책) |
| 키워드 | "렌탈" 사용 금지 (시스템 프롬프트로 강제) |

---

## 10. 구현 단계 (Claude Code에 단계별 요청)

### Phase 1: 인프라 (반나절)
1. `wrangler init ajasky-pseo` (TypeScript, Hono 템플릿)
2. `wrangler d1 create ajasky-pseo-db` → wrangler.toml에 binding 추가
3. `wrangler r2 bucket create ajasky-media` → binding 추가
4. `src/db/schema.sql` + `seed.sql` 작성 + `wrangler d1 execute` 로 적용
5. `wrangler dev` 로 로컬 동작 확인

### Phase 2: 라우팅 (1~2일)
6. Hono 셋업 + Host 미들웨어
7. 3개 라우트: `/`, `/{board_slug}`, `/{board_slug}/{post_slug}`
8. 9-섹션 템플릿 컴포넌트 (`templates/post-template.tsx`)
9. 보드 목록 + 페이지네이션
10. `wrangler dev` 에서 더미 데이터로 렌더 확인

### Phase 3: SEO (1일)
11. `/sitemap.xml` + 분할 sitemap
12. `/robots.txt`
13. JSON-LD + meta 헬퍼
14. Google Rich Results Test 통과 확인

### Phase 4: API + Python 통합 (1일)
15. `POST /api/posts` + Bearer token
16. 기존 Python `publish.py` 작성 (Worker API 호출)
17. 더미 글 1개로 end-to-end 테스트

### Phase 5: 콘텐츠 (지속)
18. Gemini 9-섹션 시스템 프롬프트 튜닝 (`prompt-template.txt`)
19. 보유 경기/인천 키워드 → publish 큐 변환
20. 일일 cron 가동 (1~2건/일)

### Phase 6: 도메인 연결 (점진)
21. 메인 도메인부터 (ajasky.kr) Cloudflare → Worker 라우트 연결
22. 안정 확인 후 나머지 39개 도메인 점진 이전
23. 도메인마다 sites 테이블에 row + 네이버 사이트 인증 코드 입력

---

## 11. 검증 체크리스트 (Phase 4 완료 시)

- [ ] `view-source` 에서 JSON-LD 검증 (Google Rich Results Test)
- [ ] `/sitemap.xml` 200 응답, 인덱스 정상
- [ ] `/sitemap-posts-1.xml` URL 1,000개 정상
- [ ] `/robots.txt` 정상
- [ ] 네이버 웹마스터에서 사이트 인증 통과
- [ ] PageSpeed Insights 90+ 점 (Worker는 빠름, 캐싱 헤더만 점검)
- [ ] 모바일 반응형
- [ ] 보드 페이지에서 새 글 노출
- [ ] 같은 slug 재발행 시 409 반환

---

## 12. 사장님 기존 자산 활용 매핑

| 기존 자산 | 새 시스템에서의 역할 |
|---|---|
| 40개 region-specific 도메인 | `sites` 테이블에 row 등록 (멀티 도메인) |
| 90k 지역 키워드 데이터 | publish 큐의 `(region × board × longtail)` 변수 풀 |
| Selenium + Gemini 파이프라인 | `content-pipeline/generate.py` 그대로 재사용 |
| `NAVER_SEO_GUIDELINES.md` | 9-섹션 템플릿 / 메타 태그 검증 기준 |
| jigoosky / oo9qudcjs 분석 | 글 스타일 변형 (정형형 + 스토리형 + 단계형 섞기) |
| Cloudflare Pages 환경 | Worker로 점진 이전 (도메인 단위) |
| Naver Cafe (cafe.naver.com/ajasky) | 글 푸터에 카페 링크 자동 삽입 |
| 010-9249-0510 | sites 테이블 phone 컬럼, 글 푸터/CTA |

---

## 13. 주의 / 리스크

1. **D1 동시 쓰기**: SQLite 기반, 동시 INSERT 충돌 가능 → Python에서 직렬 또는 랜덤 백오프
2. **Worker CPU 한도**: 무료 10ms / 유료 50ms — 큰 sitemap은 분할 캐싱 (Cache API) 필요
3. **네이버 색인**: 대량 신규 페이지는 sitemap만으론 색인 안 됨 (사장님이 이미 경험) → 네이버 웹마스터에서 일부는 수동 수집 요청
4. **AI 콘텐츠 패턴화**: 9-섹션이 너무 똑같으면 네이버 D.I.A.가 패턴 학습 → 보드별/월별 템플릿 변형 필요. 사장님이 분석하신 jigoosky(스토리형) / oo9qudcjs(단계형) 스타일을 30% 정도 섞어서 다양화
5. **OG 이미지 1장 재사용 (sfskycar 패턴)**: 비용 0이지만 너무 균일 → 보드별 1장씩 8장으로 분리 권장
6. **부정 SEO 백링크**: 사장님 기존 ajasky01092490510.com에 wormsz 백링크 126개 이슈 있음 — 새 도메인은 깨끗하게 시작. 기존 도메인 이전 시 Search Console 디스어보우 먼저
7. **D1 백업**: D1은 자동 백업 있지만 매주 SQL dump 권장 (wrangler d1 export)

---

## 14. 다음 단계 (Claude Code에 요청할 것)

이 문서를 기반으로 Claude Code에게 **Phase 단위로 순차 요청**한다:

1. **"Phase 1 셋업: wrangler 프로젝트 + D1 생성 + schema.sql 적용 + 초기 sites/boards INSERT 스크립트 작성"**
2. **"Phase 2: Hono + 라우팅 3개(/, /{board}, /{board}/{post}) + 9-섹션 post-template 구현"**
3. **"Phase 3: sitemap + robots + meta + JSON-LD 헬퍼 구현"**
4. **"Phase 4: POST /api/posts 엔드포인트 + Python publish.py 통합 + end-to-end 테스트"**
5. Phase 5 이후는 콘텐츠 운영 단계 — 자체 진행

각 Phase 완료 후 `wrangler tail` 로 동작 확인. Phase 1 끝나기 전에 Phase 2 진행 X.

---

## 15. 참고 자료

- sfskycar.com 사이트맵: https://sfskycar.com/sitemap.xml (47,983 URL, 9-섹션 글 구조 분석 완료)
- Hono 공식 문서: https://hono.dev
- Cloudflare D1 문서: https://developers.cloudflare.com/d1
- 네이버 Search Advisor: https://searchadvisor.naver.com
- 사장님 기존 NAVER_SEO_GUIDELINES.md (병행 참조)

---

**프로젝트 시작 전 사장님 확인 필요:**
- [ ] WORKER_API_TOKEN 생성 + .env에 보관
- [ ] 메인 시작 도메인 결정 (도메인은 나중에 따로 줄게)
- [ ] 기존 Python 파이프라인 코드 위치 확인 → content-pipeline/ 으로 이전
- [ ] 8개 보드 longtail 풀 초기 데이터 (보드당 50개씩 = 400개)
- [ ] OG 이미지 8장 (보드별 1장)
