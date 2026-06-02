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
