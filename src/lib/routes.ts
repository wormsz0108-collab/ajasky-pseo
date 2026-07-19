export const QUOTE_GUIDE_SLUG = '스카이차-견적-가이드';
// sitemap urlFor()는 encodeURI를 적용하므로 원문 경로를, HTML href/canonical은 인코딩 경로를 쓴다.
export const QUOTE_GUIDE_PATH = `/${QUOTE_GUIDE_SLUG}`;
export const QUOTE_GUIDE_URL_PATH = `/${encodeURIComponent(QUOTE_GUIDE_SLUG)}`;
