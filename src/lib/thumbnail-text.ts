// 썸네일 텍스트 분해
// 검색 쿼리 일치성 우선: 큰 글자에 "지역 + 메인키워드", 리본엔 차별자

export interface ThumbnailText {
  ribbon: string;            // 핑크 리본 (작게)
  headlinePrefix: string;    // 큰 글자 첫 줄 (예: "전북")
  headlineHighlight: string; // 큰 글자 둘째 줄, 노랑 밑줄 (예: "스카이차")
}

export function buildThumbnailText(region: string, boardTitle: string): ThumbnailText {
  const parts = boardTitle.split(/\s+/);

  // 2단어 보드 (스카이차 비용, 스카이차 일대, 스카이 작업차 …)
  // → 둘째 단어를 리본, 첫째 단어를 강조
  if (parts.length === 2) {
    return {
      ribbon: parts[1],
      headlinePrefix: region,
      headlineHighlight: parts[0],
    };
  }

  // 1단어 보드라도 접미사로 자연 분리 가능 (고소작업차량 → 고소작업 + 차량)
  // 좁은 카드에서 한 단어가 길면 노란 밑줄이 거대한 박스로 변하므로 시각적으로도 필수
  const suffixMatch = boardTitle.match(/^(.+?)(차량|작업차|이용료|작업)$/);
  if (suffixMatch && suffixMatch[1].length >= 2) {
    return {
      ribbon: suffixMatch[2],
      headlinePrefix: region,
      headlineHighlight: suffixMatch[1],
    };
  }

  // 그 외 1단어 보드 (스카이차) — 차별자 없음 → 지역을 리본으로 fallback
  return {
    ribbon: region,
    headlinePrefix: '',
    headlineHighlight: boardTitle,
  };
}
