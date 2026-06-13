import { html } from 'hono/html';

interface ThumbnailProps {
  imageUrl: string;
  ribbon: string;                   // 작은 리본 (차별자: 비용, 일대 …)
  headlinePrefix: string;           // 큰 첫 줄 (보통 지역명, 비어있을 수 있음)
  headlineHighlight: string;        // 큰 둘째 줄, 노랑 밑줄 (메인 키워드)
  tag?: string;                     // 검정 바 위 짧은 문구
  brandName: string;
  phone: string;
  alt?: string;
  eager?: boolean;                  // 대표(히어로) 이미지면 true → loading=eager + fetchpriority=high
}

export function Thumbnail(props: ThumbnailProps) {
  const {
    imageUrl, ribbon, headlinePrefix, headlineHighlight,
    tag = '24시 전국 배차 / 안전 책임 작업',
    brandName, phone, alt = '', eager = false,
  } = props;

  // 대표 이미지는 lazy 금지 — 네이버/구글이 대표 썸네일로 인식하고 LCP(로딩속도)도 개선.
  const loadAttr = eager ? html`loading="eager" fetchpriority="high"` : html`loading="lazy"`;

  // og/ 경로는 Python compose_og 로 디자인(리본/헤드라인/브랜드바)이 이미 baked in.
  // 그 위에 HTML 오버레이 또 그리면 텍스트가 두 번 겹쳐 보이므로 plain img만 출력.
  // photos/ 등 raw 사진이면 기존 HTML 오버레이로 디자인 입힘.
  const isBaked = imageUrl.includes('/og/');
  if (isBaked) {
    return html`
      <div class="hero hero-baked">
        <img src="${imageUrl}" alt="${alt}" width="1080" height="1080" ${loadAttr}>
      </div>
    `;
  }

  return html`
    <div class="hero">
      <img src="${imageUrl}" alt="${alt}" width="1080" height="1080" ${loadAttr}>
      <div class="side"><span class="vt">AJASKY</span></div>
      <span class="ribbon">${ribbon}</span>
      <div class="head">
        ${headlinePrefix ? html`${headlinePrefix}<br>` : ''}<span class="underline">${headlineHighlight}</span>
      </div>
      <div class="bar">
        <div class="tag">${tag}</div>
        <div class="brand">
          <span class="name">${brandName}</span>
          <span class="dot"></span>
          <span class="tel">${phone}</span>
        </div>
      </div>
    </div>
  `;
}
