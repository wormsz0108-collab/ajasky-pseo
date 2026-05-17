// 썸네일 텍스트 분해
// 검색 쿼리 일치성 우선: 큰 글자에 "지역 + 메인키워드", 리본엔 차별자

export interface ThumbnailText {
  ribbon: string;            // 핑크 리본 (작게)
  headlinePrefix: string;    // 큰 글자 첫 줄 (예: "전북")
  headlineHighlight: string; // 큰 글자 둘째 줄, 노랑 밑줄 (예: "스카이차")
}

// 보드별 명시적 매핑 — 리본에는 항상 카테고리(보드 차별자)가 들어감. 지역명 fallback 금지.
const BOARD_THUMBNAIL_MAP: Record<string, { ribbon: string; main: string }> = {
  '스카이차':      { ribbon: '스카이차', main: '스카이차' },
  '스카이차 일대':  { ribbon: '일대',    main: '스카이차' },
  '스카이 작업차':  { ribbon: '작업차',  main: '스카이차' },
  '스카이차 요금':  { ribbon: '요금',    main: '스카이차' },
  '스카이차 비용':  { ribbon: '비용',    main: '스카이차' },
  '스카이차 가격':  { ribbon: '가격',    main: '스카이차' },
  '스카이차 이용료': { ribbon: '이용료',  main: '스카이차' },
  '고소작업차량':   { ribbon: '차량',    main: '고소작업' },
};

export function buildThumbnailText(region: string, boardTitle: string): ThumbnailText {
  const mapped = BOARD_THUMBNAIL_MAP[boardTitle];
  if (mapped) {
    return {
      ribbon: mapped.ribbon,
      headlinePrefix: region,
      headlineHighlight: mapped.main,
    };
  }
  // 알 수 없는 보드면 안전 fallback (지역명 절대 리본에 들어가지 않게)
  return {
    ribbon: boardTitle,
    headlinePrefix: region,
    headlineHighlight: boardTitle,
  };
}
