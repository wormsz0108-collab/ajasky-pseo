/**
 * 이미지/리소스 URL을 외부 스크래퍼(네이버 Yeti·카카오·페이스북)가 그대로 fetch 할 수 있도록
 * 절대 URL + 퍼센트 인코딩 형태로 정규화한다.
 *
 * og:image 는 Open Graph 규격상 절대 URL 이어야 하고, 한글 파일명은 퍼센트 인코딩돼 있어야
 * 스크래퍼가 404 없이 가져갈 수 있다. (브라우저는 자동 처리하지만 스크래퍼는 그렇지 않다.)
 *
 * - 상대경로(`/media/og/...`)면 `https://{domain}` 을 붙인다.
 * - 한글 등 비ASCII 문자가 있으면 encodeURI 로 퍼센트 인코딩한다.
 *   이미 인코딩된 URL(`%EC...`)은 비ASCII 가 없으므로 그대로 두어 이중 인코딩을 피한다.
 */
export function absoluteImageUrl(raw: string, domain: string): string {
  let url = /^https?:\/\//i.test(raw)
    ? raw
    : `https://${domain}${raw.startsWith('/') ? '' : '/'}${raw}`;
  if (/[^\x00-\x7F]/.test(url)) {
    url = encodeURI(url);
  }
  return url;
}
