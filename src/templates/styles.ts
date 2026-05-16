export const STYLES = `
:root{
  --bg:#ffffff;
  --bg-soft:#f9fafb;
  --text:#111827;
  --text-soft:#4b5563;
  --meta:#6b7280;
  --line:#e5e7eb;
  --line-strong:#d1d5db;
  --brand:#1f2937;
  --accent:#ec4899;
  --accent-soft:#fdf2f8;
  --link:#1d4ed8;
  --radius:14px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;background:var(--bg);color:var(--text);
  font-family:"Pretendard Variable","Pretendard",-apple-system,BlinkMacSystemFont,"Segoe UI","Apple SD Gothic Neo","Noto Sans KR",sans-serif;
  font-size:17px;line-height:1.8;-webkit-font-smoothing:antialiased;
}
a{color:inherit}
img{max-width:100%;display:block;height:auto}

.top{border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(255,255,255,.92);backdrop-filter:saturate(180%) blur(8px);z-index:20}
.top-inner{max-width:1180px;margin:0 auto;padding:14px 20px;display:flex;align-items:center;gap:24px}
.logo{font-weight:700;font-size:18px;letter-spacing:-.02em;display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--text);flex-shrink:0;white-space:nowrap}
.logo .dot{width:10px;height:10px;border-radius:3px;background:var(--accent);flex-shrink:0}
.nav{display:flex;gap:18px;font-size:15px;color:var(--text-soft);min-width:0;overflow:hidden;flex-wrap:nowrap}
.nav a{flex-shrink:0;white-space:nowrap}
.nav a{text-decoration:none;padding:6px 0;border-bottom:2px solid transparent}
.nav a.on,.nav a:hover{color:var(--text);border-bottom-color:var(--accent)}
.top-cta{margin-left:auto;display:flex;align-items:center;gap:8px;background:var(--accent);color:#fff;text-decoration:none;padding:10px 16px;border-radius:999px;font-weight:600;font-size:15px;box-shadow:0 6px 16px -6px rgba(236,72,153,.5);white-space:nowrap}
.top-cta:hover{filter:brightness(1.08)}
.top-cta svg{width:16px;height:16px}

.wrap{max-width:760px;margin:0 auto;padding:32px 20px 80px}
.wrap-wide{max-width:1180px;margin:0 auto;padding:32px 20px 80px}
.breadcrumb{font-size:13px;color:var(--meta);margin-bottom:14px}
.breadcrumb a{color:var(--meta);text-decoration:none}
.breadcrumb .sep{margin:0 6px;opacity:.6}

h1.title{font-size:30px;line-height:1.35;letter-spacing:-.02em;margin:6px 0 12px;font-weight:800}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;color:var(--meta);font-size:14px;margin-bottom:24px}
.pill{background:var(--bg-soft);border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:13px;color:var(--text-soft)}

/* THUMBNAIL hero — pink/yellow/black AJAS signature */
.hero{position:relative;aspect-ratio:1/1;background:#000;border-radius:var(--radius);overflow:hidden;margin:0 0 28px;box-shadow:0 18px 40px -18px rgba(15,23,42,.35);container-type:inline-size;isolation:isolate}
.hero img{width:100%;height:100%;object-fit:cover;filter:brightness(.78) contrast(1.05)}
.hero .side{position:absolute;top:0;bottom:0;left:0;width:7%;z-index:2;background:#ffd200;display:flex;align-items:center;justify-content:center}
.hero .side .vt{writing-mode:vertical-rl;transform:rotate(180deg);font-weight:800;letter-spacing:.5em;color:#000;font-size:3cqw}
.hero .ribbon{position:absolute;top:8%;left:6%;z-index:3;background:var(--accent);color:#fff;padding:1.4cqw 3.6cqw;font-weight:900;font-size:6cqw;letter-spacing:-.01em;transform:rotate(-3deg);box-shadow:0 6px 0 rgba(0,0,0,.35);border-radius:4px}
.hero .head{position:absolute;left:10%;right:6%;top:30%;z-index:2;color:#fff;font-family:"Pretendard Variable","Pretendard",sans-serif;font-weight:900;line-height:1.02;letter-spacing:-.025em;font-size:16cqw;text-shadow:-3px -3px 0 #000,3px -3px 0 #000,-3px 3px 0 #000,3px 3px 0 #000,0 -3px 0 #000,0 3px 0 #000,-3px 0 0 #000,3px 0 0 #000}
.hero .head .underline{display:inline-block;background:linear-gradient(180deg,transparent 60%,#ffd200 60%);padding:0 .12em}
.hero .bar{position:absolute;left:0;right:0;bottom:0;z-index:2;background:#000;color:#fff;padding:5.5cqw 5% 5cqw;text-align:center;clip-path:polygon(0 18%,100% 0,100% 100%,0 100%)}
.hero .bar .tag{font-size:2.6cqw;font-weight:600;color:#cfcfcf;line-height:1.3;margin-bottom:1.6cqw;letter-spacing:-.01em}
.hero .bar .brand{display:flex;align-items:center;justify-content:center;gap:3cqw;font-size:4cqw;font-weight:900;letter-spacing:-.02em}
.hero .bar .brand .name{color:#ffd200}
.hero .bar .brand .dot{width:1cqw;height:1cqw;border-radius:50%;background:var(--accent);box-shadow:0 0 0 .4cqw rgba(236,72,153,.25)}
.hero .bar .brand .tel{color:#fff;font-variant-numeric:tabular-nums}

/* TOC */
.toc{border:1px solid var(--line);background:var(--bg-soft);border-radius:var(--radius);padding:18px 22px 16px;margin:0 0 36px}
.toc-h{display:flex;align-items:center;justify-content:space-between;font-size:14px;font-weight:700;color:var(--text);margin-bottom:8px;letter-spacing:.02em}
.toc-h .badge{font-size:11px;color:var(--meta);font-weight:500;background:#fff;border:1px solid var(--line);padding:2px 8px;border-radius:6px}
.toc ol{margin:6px 0 0;padding:0;list-style:none;counter-reset:toci}
.toc li{padding:5px 0;font-size:15px;color:var(--text-soft);counter-increment:toci;display:flex;gap:10px}
.toc li::before{content:counter(toci,decimal-leading-zero);color:var(--accent);font-weight:700;min-width:22px;font-variant-numeric:tabular-nums}
.toc a{text-decoration:none;color:inherit}
.toc a:hover{color:var(--text)}

/* sections */
section h2{font-size:22px;line-height:1.4;margin:48px 0 14px;font-weight:800;letter-spacing:-.01em;display:flex;align-items:baseline;gap:10px;padding-bottom:10px;border-bottom:2px solid var(--text)}
section h2 .num{color:var(--accent);font-size:18px;font-weight:800;font-variant-numeric:tabular-nums;min-width:28px}
section h3{font-size:16px;margin:24px 0 8px;font-weight:700;color:var(--text)}
section p{margin:12px 0;color:var(--text-soft)}
section ul,section ol{margin:10px 0 14px;padding-left:22px;color:var(--text-soft)}
section li{margin:4px 0}

/* CTA card */
.cta-card{margin:36px 0;padding:18px 22px;background:linear-gradient(135deg,#fdf2f8 0%,#fff 100%);border:1px solid #fbcfe8;border-radius:var(--radius);display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.cta-card .text{flex:1;min-width:200px}
.cta-card .text strong{display:block;font-size:16px;color:var(--text);margin-bottom:2px}
.cta-card .text span{font-size:13px;color:var(--text-soft)}
.cta-card .btns{display:flex;gap:8px}
.btn{text-decoration:none;padding:10px 16px;border-radius:10px;font-weight:600;font-size:14px;display:inline-flex;align-items:center;gap:6px}
.btn.primary{background:var(--accent);color:#fff}
.btn.outline{background:#fff;color:var(--text);border:1px solid var(--line-strong)}

/* FAQ */
.faq{margin-top:24px;border-top:1px solid var(--line)}
.faq-item{padding:18px 0;border-bottom:1px solid var(--line)}
.faq-q{font-weight:700;color:var(--text);margin:0 0 6px;font-size:16px;display:flex;gap:8px}
.faq-q .qmark{color:var(--accent);font-weight:800}
.faq-a{color:var(--text-soft);margin:0;padding-left:24px}

/* same-board related posts list */
.related-list{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:8px}
.related-list li{margin:0}
.related-list a{display:flex;align-items:center;gap:10px;padding:12px 14px;border:1px solid var(--line);border-radius:10px;text-decoration:none;background:#fff;transition:border-color .2s,transform .2s}
.related-list a:hover{border-color:var(--accent);transform:translateX(2px)}
.related-region{font-size:12px;color:#fff;background:var(--accent);padding:3px 8px;border-radius:6px;font-weight:600;flex-shrink:0;white-space:nowrap}
.related-title{font-size:14px;color:var(--text);font-weight:500;line-height:1.4}

/* region chips */
.region-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.region-list a{text-decoration:none;background:var(--bg-soft);border:1px solid var(--line);padding:6px 12px;border-radius:8px;font-size:13px;color:var(--text-soft)}
.region-list a:hover{border-color:var(--accent);color:var(--accent)}

/* footer */
footer{border-top:1px solid var(--line);margin-top:64px;padding:40px 20px;background:var(--bg-soft);color:var(--meta);font-size:13px}
footer .f-inner{max-width:1180px;margin:0 auto;display:grid;gap:18px;grid-template-columns:1fr 2fr}
footer h4{font-size:13px;margin:0 0 8px;color:var(--text);font-weight:700}
footer a{color:var(--meta);text-decoration:none}
footer a:hover{color:var(--text)}

/* board page — card grid */
.page-h{margin:8px 0 24px}
.page-h h1{font-size:34px;line-height:1.25;margin:0 0 6px;font-weight:800;letter-spacing:-.02em}
.page-h .desc{color:var(--meta);font-size:15px;margin:0}

.grid{display:grid;gap:22px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.card{display:flex;flex-direction:column;text-decoration:none;color:inherit;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;background:#fff;transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease}
.card:hover{transform:translateY(-4px);box-shadow:0 18px 30px -18px rgba(0,0,0,.18);border-color:transparent}
.card .thumb{position:relative}
.card .thumb .hero{margin:0;border-radius:0;box-shadow:none}
.card .body{padding:14px 16px 18px}
.card .body .ttl{font-size:16px;font-weight:700;line-height:1.4;color:var(--text);margin:0 0 6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card .body .mt{font-size:12px;color:var(--meta);display:flex;gap:8px}

/* pagination */
.pag{display:flex;justify-content:center;gap:6px;margin:40px 0 0}
.pag a,.pag span{padding:8px 14px;border-radius:8px;font-size:14px;text-decoration:none;color:var(--text-soft);border:1px solid var(--line)}
.pag a:hover{border-color:var(--accent);color:var(--accent)}
.pag .now{background:var(--accent);color:#fff;border-color:var(--accent)}

/* home — board overview */
.boards-grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));margin:24px 0 40px}
.board-tile{text-decoration:none;color:inherit;display:flex;flex-direction:column;justify-content:center;align-items:center;aspect-ratio:1.4/1;background:#0f172a;color:#fff;border-radius:var(--radius);padding:14px;position:relative;overflow:hidden;text-align:center;transition:transform .2s ease}
.board-tile::before{content:"";position:absolute;inset:0;background:linear-gradient(135deg,var(--accent) 0%,#0f172a 100%);opacity:.9}
.board-tile span{position:relative;font-weight:800;font-size:18px;letter-spacing:-.02em;line-height:1.25}
.board-tile small{position:relative;display:block;font-size:11px;color:rgba(255,255,255,.75);margin-top:4px;font-weight:500}
.board-tile:hover{transform:translateY(-2px)}
.board-tile:hover::before{opacity:1}

.section-h{display:flex;align-items:baseline;justify-content:space-between;margin:36px 0 16px}
.section-h h2{margin:0;font-size:22px;font-weight:800;letter-spacing:-.02em}
.section-h a{text-decoration:none;color:var(--accent);font-size:13px;font-weight:600}

@media (max-width:1024px){
  .nav{display:none}
}
@media (max-width:640px){
  h1.title{font-size:24px}
  section h2{font-size:19px}
  .top-cta{padding:8px 12px;font-size:13px}
  .page-h h1{font-size:26px}
  footer .f-inner{grid-template-columns:1fr}
  /* 모바일 보드 타일 — 2열 강제로 압축 (CTA에 빨리 닿게) */
  .boards-grid{grid-template-columns:repeat(2,1fr);gap:10px}
  .board-tile{aspect-ratio:1.2/1;padding:12px}
  .board-tile span{font-size:15px}
}
`;
