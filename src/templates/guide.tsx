import { html, raw } from 'hono/html';
import type { Site, Board } from '../types';
import { QUOTE_GUIDE_URL_PATH } from '../lib/routes';
import { Layout } from './layout';

export const GUIDE_FAQ = [
  {
    q: '스카이차 비용은 무엇으로 결정되나요?',
    a: '작업 높이와 수평 작업 반경, 차량 진입과 설치 공간, 교통 통제 필요 여부, 작업 시간과 대기 시간, 야간 작업 여부를 함께 확인해 산정합니다.',
  },
  {
    q: '건물 층수만 알려주면 견적을 받을 수 있나요?',
    a: '층수는 시작 정보입니다. 차량을 세울 위치와 작업 지점 사이의 거리, 전선이나 수목 같은 장애물, 도로 폭도 함께 알려주면 더 정확한 상담이 가능합니다.',
  },
  {
    q: '현장 사진은 어떤 것을 준비해야 하나요?',
    a: '건물 전체와 작업 지점, 차량 진입로, 차량을 세울 공간이 한눈에 보이는 사진을 준비해 주세요. 도로가 좁다면 진입 방향 양쪽 사진도 도움이 됩니다.',
  },
  {
    q: '작업 시간이 길어지면 비용이 달라지나요?',
    a: '예상 작업 시간을 넘기거나 현장 대기가 발생하면 조건이 달라질 수 있습니다. 작업량과 예상 소요 시간을 상담 전에 공유하는 것이 좋습니다.',
  },
  {
    q: '야간이나 주말 작업도 상담할 수 있나요?',
    a: '가능한 일정은 현장과 배차 상황에 따라 달라집니다. 원하는 날짜와 시작 시간, 야간 여부를 알려주면 가능 여부와 조건을 확인할 수 있습니다.',
  },
  {
    q: '도로 사용이나 차량 통제가 필요한가요?',
    a: '차량이 차로 또는 보행 동선을 점유하는 현장은 안전 통제나 관련 절차가 필요할 수 있습니다. 정확한 주소와 도로 상황을 먼저 확인해야 합니다.',
  },
  {
    q: '어떤 차종이 맞는지 미리 골라야 하나요?',
    a: '직접 차종을 확정할 필요는 없습니다. 높이, 수평 거리, 진입 폭, 작업 내용과 사진을 전달하면 현장 조건에 맞는 차량을 상담할 수 있습니다.',
  },
  {
    q: '전화 전에 무엇을 정리하면 좋나요?',
    a: '정확한 주소, 작업 종류, 층수 또는 높이, 차량 진입과 주차 조건, 희망 일정, 현장 사진을 준비하면 상담 시간을 줄일 수 있습니다.',
  },
];

interface GuidePageProps {
  site: Site;
  boards: Pick<Board, 'slug' | 'title'>[];
  jsonLd: object;
}

export function QuoteGuidePage({ site, boards, jsonLd }: GuidePageProps) {
  const phoneHref = `tel:${site.phone.replace(/-/g, '')}`;
  const priceFocused = site.domain === 'wormsz1.store';
  const title = priceFocused
    ? '스카이차 비용·가격·요금 | 현장 견적 준비 가이드'
    : '전국 스카이차 비용·가격·요금 | 현장 견적 준비 가이드';
  const description = priceFocused
    ? `스카이차 비용과 가격을 좌우하는 높이, 반경, 진입로, 통제, 작업 시간과 대기 조건을 확인하고 상담 내용을 정리하세요. ${site.phone}`
    : `전국 스카이차 배차 전 높이, 반경, 진입로, 통제, 작업 시간과 대기 조건을 확인하고 현장 상담 내용을 정리하세요. ${site.phone}`;

  const script = `
    (() => {
      const form = document.getElementById('quote-form');
      const summary = document.getElementById('quote-summary');
      const status = document.getElementById('copy-status');
      if (!form || !summary || !status) return;
      const value = (id) => {
        const node = document.getElementById(id);
        return node && node.value.trim() ? node.value.trim() : '미입력';
      };
      form.addEventListener('submit', (event) => {
        event.preventDefault();
        summary.textContent = '[스카이차 현장 상담]\\n작업: ' + value('work') +
          '\\n층수·높이: ' + value('height') +
          '\\n진입 조건: ' + value('access') +
          '\\n희망 일정: ' + value('schedule') +
          '\\n주소·추가 내용: ' + value('notes');
        status.textContent = '내용을 확인한 뒤 복사해 주세요.';
      });
      document.getElementById('copy-summary')?.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(summary.textContent || '');
          status.textContent = '상담 내용이 복사되었습니다.';
        } catch {
          const range = document.createRange();
          range.selectNode(summary);
          const selection = window.getSelection();
          selection?.removeAllRanges();
          selection?.addRange(range);
          status.textContent = '선택된 내용을 복사해 주세요.';
        }
      });
    })();
  `;

  const inner = html`
    <main class="wrap guide-page">
      <nav class="breadcrumb">
        <a href="/">홈</a><span class="sep">›</span><span>스카이차 견적 준비 가이드</span>
      </nav>

      <div class="page-h guide-head">
        <p class="guide-kicker">비용을 묻기 전에 확인할 현장 조건</p>
        <h1>${title}</h1>
        <p class="desc">스카이차 비용은 층수 하나로 정해지지 않습니다. 작업 높이와 수평 거리, 차량 설치 공간과 작업 시간을 함께 확인해야 현장에 맞는 상담이 가능합니다.</p>
        <div class="guide-actions">
          <a class="btn primary" href="#quote-tool">현장 정보 정리</a>
          <a class="btn outline" href="${phoneHref}">전화 상담 ${site.phone}</a>
        </div>
      </div>

      <section id="factors">
        <h2><span class="num">01</span>비용을 좌우하는 6가지 조건</h2>
        <p>같은 층수라도 차량을 세울 위치와 작업 지점의 수평 거리가 다르면 필요한 장비와 작업 조건이 달라집니다.</p>
        <div class="guide-factors">
          <article><h3>작업 높이</h3><p>건물 층수와 실제 작업 지점의 높이를 함께 확인합니다.</p></article>
          <article><h3>수평 작업 반경</h3><p>차량 위치에서 작업 지점까지 떨어진 거리는 차종 선택에 중요합니다.</p></article>
          <article><h3>진입과 설치 공간</h3><p>도로 폭, 회전 공간, 주차 차량과 지반 상태를 확인합니다.</p></article>
          <article><h3>안전 통제 조건</h3><p>차로와 보행 동선 점유 여부에 따라 준비 범위가 달라질 수 있습니다.</p></article>
          <article><h3>작업 시간과 대기</h3><p>작업량, 예상 소요 시간, 현장 대기 가능성을 미리 공유합니다.</p></article>
          <article><h3>일정과 시간대</h3><p>희망 날짜와 시작 시간, 야간 여부와 현장 제한 시간을 확인합니다.</p></article>
        </div>
        <div class="guide-visual">
          <img src="/og-default.jpg" alt="${site.site_name} 스카이차 현장 안내 이미지" width="1080" height="1080" loading="lazy">
          <div><h3>현장 전체가 보이는 사진을 준비하세요</h3><p>견적에는 건물만 확대해 찍은 사진보다 작업 지점, 진입로, 차량 설치 위치와 주변 장애물이 함께 보이는 사진이 유용합니다.</p></div>
        </div>
      </section>

      <section id="steps">
        <h2><span class="num">02</span>전화 전에 준비할 순서</h2>
        <ol class="guide-steps">
          <li><strong>주소와 높이 확인</strong><span>정확한 현장 주소와 층수 또는 작업 높이를 확인합니다.</span></li>
          <li><strong>진입 조건 촬영</strong><span>진입로와 차량 설치 공간, 작업 지점이 보이도록 촬영합니다.</span></li>
          <li><strong>작업량 정리</strong><span>작업 종류와 예상 작업량, 소요 시간을 정리합니다.</span></li>
          <li><strong>일정 전달</strong><span>희망 날짜와 시작 시간, 통제 가능 여부를 전달합니다.</span></li>
        </ol>
      </section>

      <section id="quote-tool">
        <h2><span class="num">03</span>현장 상담 내용 정리</h2>
        <p>입력한 내용은 서버로 전송되지 않으며 이 브라우저에서 상담 문장으로만 정리됩니다.</p>
        <div class="guide-tool">
          <form id="quote-form">
            <div class="guide-fields">
              <label>작업 종류<select id="work"><option>외벽 도색·보수</option><option>간판·LED 작업</option><option>수목 전지</option><option>자재 양중</option><option>유리창 청소</option><option>기타 고소작업</option></select></label>
              <label>층수 또는 높이<input id="height" placeholder="예: 5층, 약 15m"></label>
              <label>진입·설치 조건<select id="access"><option>도로와 설치 공간이 넓음</option><option>이면도로 또는 골목</option><option>차량 통제가 필요할 수 있음</option><option>현장 확인 필요</option></select></label>
              <label>희망 일정<input id="schedule" placeholder="예: 7월 25일 오전"></label>
              <label class="full">주소와 추가 내용<textarea id="notes" placeholder="현장 주소, 수평 거리, 장애물, 예상 작업 시간을 적어 주세요."></textarea></label>
            </div>
            <button class="btn primary guide-submit" type="submit">상담 내용 정리하기</button>
          </form>
          <div class="guide-output">
            <h3>상담 전달 내용</h3>
            <p id="quote-summary">항목을 입력한 뒤 상담 내용 정리하기를 누르세요.</p>
            <button class="btn outline" id="copy-summary" type="button">상담 내용 복사</button>
            <p class="guide-status" id="copy-status" aria-live="polite">사진은 전화 연결 후 안내받은 방법으로 전달하세요.</p>
          </div>
        </div>
      </section>

      <section id="faq">
        <h2><span class="num">04</span>자주 묻는 질문</h2>
        <div class="faq">
          ${GUIDE_FAQ.map(f => html`<div class="faq-item"><p class="faq-q"><span class="qmark">Q.</span>${f.q}</p><p class="faq-a">${f.a}</p></div>`)}
        </div>
      </section>
    </main>
    <script>${raw(script)}</script>
  `;

  return Layout({
    site,
    boards,
    title,
    description,
    canonicalPath: QUOTE_GUIDE_URL_PATH,
    ogType: 'article',
    keywords: '스카이차 비용,스카이차 가격,스카이차 요금,스카이차 견적,스카이차 일대,고소작업차량',
    jsonLd,
    children: inner,
  });
}
