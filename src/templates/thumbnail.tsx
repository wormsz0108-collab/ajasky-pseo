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
}

export function Thumbnail(props: ThumbnailProps) {
  const {
    imageUrl, ribbon, headlinePrefix, headlineHighlight,
    tag = '24시 전국 배차 / 안전 책임 작업',
    brandName, phone, alt = '',
  } = props;

  return html`
    <div class="hero">
      <img src="${imageUrl}" alt="${alt}" loading="lazy">
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
