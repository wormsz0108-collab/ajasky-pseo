// 도메인별 색상·폰트 테마. 같은 Worker/템플릿이 40개 도메인에 바이트 단위로 똑같이
// 나가면 네이버/구글이 "미러 템플릿"으로 묶어 일괄 강등할 수 있으므로, site 단위로
// :root 변수(색)·폰트·모서리를 갈아끼워 크롬을 분화한다.
//
// hero/OG 이미지(노랑·검정 AJAS 시그니처)는 Python 에서 baked 되므로 건드리지 않는다.
// 여기서 바꾸는 건 헤더·CTA·링크·카드·푸터 등 CSS 로 그려지는 사이트 크롬뿐.

export interface Theme {
  css: string; // STYLES 뒤에 덧붙는 :root 오버라이드 (+ body 폰트)
  fontHref?: string; // 테마 전용 웹폰트 (없으면 기본 Pretendard 유지)
}

const THEMES: Theme[] = [
  // 0 — 핑크 (기존 시그니처, OG 리본과 동일 계열)
  {
    css: `:root{--accent:#ec4899;--accent-soft:#fdf2f8;--link:#1d4ed8;--brand:#1f2937;--radius:14px}`,
  },
  // 1 — 블루 (반듯한 인상, 모서리 좁게)
  {
    css: `:root{--accent:#2563eb;--accent-soft:#eff6ff;--link:#1d4ed8;--brand:#0f172a;--radius:10px}
body{font-family:"Noto Sans KR",-apple-system,BlinkMacSystemFont,"Segoe UI","Apple SD Gothic Neo",sans-serif}`,
    fontHref:
      'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800&display=swap',
  },
  // 2 — 그린/틸 (부드러운 인상, 모서리 넓게)
  {
    css: `:root{--accent:#0d9488;--accent-soft:#f0fdfa;--link:#0f766e;--brand:#134e4a;--radius:18px}
body{font-family:"IBM Plex Sans KR",-apple-system,BlinkMacSystemFont,"Segoe UI","Apple SD Gothic Neo",sans-serif}`,
    fontHref:
      'https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap',
  },
];

function hashStr(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h;
}

// site.id 우선(분포 안정), 없으면 domain 해시. 같은 사이트 = 항상 같은 테마.
export function pickTheme(site: { id?: number; domain: string }): Theme {
  const key = site.id != null ? site.id : hashStr(site.domain);
  return THEMES[key % THEMES.length];
}
