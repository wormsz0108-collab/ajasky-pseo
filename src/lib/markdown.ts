// body_md (Gemini가 만든 9-섹션 마크다운) → RenderedSection[]
// 의도적으로 미니멀 파서. Gemini 출력 포맷 가정:
//   ## 1. 섹션 제목 (또는 ## 섹션 제목)
//   본문 단락 (빈 줄로 구분)
//   ### h3 제목
//   1. 번호 리스트
//   - 불릿 리스트
//
// 인라인은 **굵게**만 지원 (Gemini 출력에 종종 포함). 기울임/링크는 미지원.

import type { RenderedSection } from '../templates/post';

const escapeHtml = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// 이스케이프 후 인라인 강조(**굵게**) 변환. 별표는 escape 영향 없음.
const inline = (s: string) =>
  escapeHtml(s).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

// 제원 비교표 raw 통과용 살균기. body_md 는 DB 값이라 이 경로로 임의 마크업이
// 올 수 있다는 전제하에, 표 구조 태그만 허용하고 속성도 화이트리스트로 제한한다.
// 허용 밖 태그는 마크업만 제거(텍스트는 escape 후 보존)해 스크립트/이벤트 핸들러/
// 인라인 이미지 등 주입 벡터를 원천 차단한다.
const SPEC_TAG_OK = new Set(['div', 'table', 'thead', 'tbody', 'caption', 'tr', 'th', 'td']);
const SPEC_ATTR_OK: Record<string, RegExp> = {
  class: /^(spec-table-wrap|spec-table|spec-caption)$/,
  scope: /^(col|row)$/,
  colspan: /^\d{1,2}$/,
  rowspan: /^\d{1,2}$/,
};
function sanitizeSpecTable(s: string): string {
  // 스크립트/스타일 블록은 내용째 제거
  s = s.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, '');
  const out: string[] = [];
  let last = 0;
  const tagRe = /<\/?([a-zA-Z][a-zA-Z0-9]*)((?:[^>"']|"[^"]*"|'[^']*')*)>/g;
  let m: RegExpExecArray | null;
  while ((m = tagRe.exec(s)) !== null) {
    // 태그 사이 텍스트는 escape 후 보존
    out.push(escapeHtml(s.slice(last, m.index)));
    last = tagRe.lastIndex;
    const tag = m[1].toLowerCase();
    if (!SPEC_TAG_OK.has(tag)) continue; // 허용 밖 태그 → 마크업 제거
    const closing = m[0].startsWith('</');
    if (closing) { out.push(`</${tag}>`); continue; }
    // 허용 속성만 재구성 (그 외 on*·style·href 등 전부 폐기)
    let attrs = '';
    const attrRe = /([a-zA-Z][a-zA-Z0-9-]*)\s*=\s*"([^"]*)"|([a-zA-Z][a-zA-Z0-9-]*)\s*=\s*'([^']*)'/g;
    let a: RegExpExecArray | null;
    while ((a = attrRe.exec(m[2])) !== null) {
      const name = (a[1] || a[3]).toLowerCase();
      const val = a[2] !== undefined ? a[2] : a[4];
      const ok = SPEC_ATTR_OK[name];
      if (ok && ok.test(val)) attrs += ` ${name}="${escapeHtml(val)}"`;
    }
    out.push(`<${tag}${attrs}>`);
  }
  out.push(escapeHtml(s.slice(last)));
  return out.join('');
}

interface Block {
  headLine: string;
  bodyLines: string[];
}

export function parseBodyMarkdown(md: string): RenderedSection[] {
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let cur: Block | null = null;

  for (const line of lines) {
    const m = line.match(/^##\s+(.+)$/);
    if (m) {
      if (cur) blocks.push(cur);
      cur = { headLine: m[1].trim(), bodyLines: [] };
    } else {
      // ## 이전 줄은 무시 (h1, 도입 텍스트 등)
      if (cur) cur.bodyLines.push(line);
    }
  }
  if (cur) blocks.push(cur);

  return blocks.map((b, i) => {
    let title = b.headLine;
    const numPrefix = title.match(/^(\d+)\.\s*(.+)$/);
    if (numPrefix) title = numPrefix[2].trim();
    return {
      num: String(i + 1).padStart(2, '0'),
      anchor: `s${i + 1}`,
      title,
      bodyHtml: renderBlock(b.bodyLines.join('\n')),
    };
  });
}

function renderBlock(md: string): string {
  const out: string[] = [];
  const lines = md.split('\n');
  let paraBuf: string[] = [];
  let listType: 'ol' | 'ul' | null = null;

  const flushPara = () => {
    if (paraBuf.length === 0) return;
    const text = paraBuf.join(' ').trim();
    if (text) out.push(`<p>${inline(text)}</p>`);
    paraBuf = [];
  };
  const closeList = () => {
    if (listType) { out.push(`</${listType}>`); listType = null; }
  };

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '');
    // 원시 HTML 통과: 파이프라인이 주입한 제원 비교표 블록(한 줄)만 이스케이프 없이 출력.
    // 옛 글 body_md 엔 이 클래스가 없어 렌더가 그대로 불변. body_md 는 DB 값이므로
    // 신뢰에 기대지 않고 표 전용 태그 화이트리스트로 살균한 뒤 출력(스크립트/이벤트/임의 태그 차단).
    if (line.trim().startsWith('<div class="spec-table-wrap"')) {
      flushPara(); closeList();
      out.push(sanitizeSpecTable(line.trim()));
      continue;
    }
    const h3 = line.match(/^###\s+(.+)$/);
    const ol = line.match(/^\d+\.\s+(.+)$/);
    const ul = line.match(/^[-*]\s+(.+)$/);

    if (h3) {
      flushPara(); closeList();
      out.push(`<h3>${inline(h3[1].trim())}</h3>`);
    } else if (ol) {
      flushPara();
      if (listType !== 'ol') { closeList(); out.push('<ol>'); listType = 'ol'; }
      out.push(`<li>${inline(ol[1].trim())}</li>`);
    } else if (ul) {
      flushPara();
      if (listType !== 'ul') { closeList(); out.push('<ul>'); listType = 'ul'; }
      out.push(`<li>${inline(ul[1].trim())}</li>`);
    } else if (line.trim() === '') {
      flushPara(); closeList();
    } else {
      closeList();
      paraBuf.push(line);
    }
  }
  flushPara(); closeList();
  return out.join('\n');
}
