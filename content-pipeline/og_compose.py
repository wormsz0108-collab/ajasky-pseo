"""OG 이미지 자동 합성.

본 사진(1:1) + 디자인 시안의 오버레이(좌측 노란 띠, 핑크 리본, 굵은 헤드라인, 하단 검정 브랜드 바)
를 합성해서 jpeg bytes 반환. 네이버 검색 썸네일에 텍스트가 박혀 노출됨.

폰트는 GitHub Actions runner 의 기본 폰트가 한글을 지원하지 않으므로,
Noto Sans CJK 폰트를 fonts/ 에 같이 커밋 (publish.yml 에서 install 으로 대체 가능).
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# 1080×1080 1:1 출력 (네이버 권장)
OUT_W = 1080
OUT_H = 1080

# 색
COLOR_YELLOW = "#ffd200"
COLOR_PINK = "#ec4899"
COLOR_BLACK = "#000000"
COLOR_WHITE = "#ffffff"
COLOR_GRAY = "#cfcfcf"

# 비율 (시안의 cqw 단위에 대응)
SIDE_WIDTH = int(OUT_W * 0.07)
HEAD_LINE_FONT_PX = int(OUT_W * 0.16)   # 큰 헤드라인 글자 크기
RIBBON_FONT_PX = int(OUT_W * 0.06)      # 핑크 리본 글자
BAR_HEIGHT = int(OUT_H * 0.16)
BAR_TAG_FONT_PX = int(OUT_W * 0.026)
BAR_BRAND_FONT_PX = int(OUT_W * 0.04)


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    """한글 폰트 우선 탐색. 없으면 default."""
    candidates = [
        # GitHub Actions ubuntu-latest 에 기본 설치되는 Noto CJK
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        # Windows 로컬 폴백
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _fit_font(text: str, max_w: int, start_size: int, min_size: int = 40) -> ImageFont.FreeTypeFont:
    """text 가 max_w 안에 들어가도록 폰트 크기 축소. start_size 부터 min_size 까지."""
    size = start_size
    while size > min_size:
        font = _find_font(size)
        bbox = font.getbbox(text)
        if (bbox[2] - bbox[0]) <= max_w:
            return font
        size -= 8
    return _find_font(min_size)


def _stroke_text(draw: ImageDraw.ImageDraw, xy, text, font, fill, stroke_fill, stroke_width):
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def compose_og(
    source_image_bytes: bytes,
    *,
    ribbon: str,           # 예: "비용"
    headline_prefix: str,  # 예: "전북" (비어있을 수 있음)
    headline_main: str,    # 예: "스카이차"
    tag: str = "24시 전국 배차 / 안전 책임 작업",
    brand_name: str = "아자스카이",
    phone: str = "010-9249-0510",
    theme: Optional[dict] = None,  # theme.pick_og_theme(domain) 결과. None이면 기존 핑크.
) -> bytes:
    # 도메인 테마 색 (없으면 기존 시그니처 = 노랑/핑크/검정)
    t = theme or {}
    c_side = t.get("side", COLOR_YELLOW)
    c_ribbon = t.get("ribbon", COLOR_PINK)
    c_underline = t.get("underline", COLOR_YELLOW)
    c_bar = t.get("bar", COLOR_BLACK)
    c_name = t.get("name", COLOR_YELLOW)
    c_dot = t.get("dot", COLOR_PINK)
    # 1. 본 사진을 1080×1080으로 크롭/리사이즈 + 어둡게
    base = Image.open(BytesIO(source_image_bytes)).convert("RGB")
    base = _fit_center_crop(base, OUT_W, OUT_H)
    # 어두운 오버레이 (0.78 brightness 효과)
    dark = Image.new("RGB", (OUT_W, OUT_H), (0, 0, 0))
    base = Image.blend(base, dark, 0.22)

    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)

    # 2. 좌측 세로 띠
    draw.rectangle([0, 0, SIDE_WIDTH, OUT_H], fill=c_side)

    # 3. 핑크 리본 (좌상)
    if ribbon:
        rfont = _find_font(RIBBON_FONT_PX)
        # ribbon 위치: 좌상 8%, 6%
        rx = int(OUT_W * 0.06)
        ry = int(OUT_H * 0.08)
        bbox = draw.textbbox((0, 0), ribbon, font=rfont)
        rw = bbox[2] - bbox[0]
        rh = bbox[3] - bbox[1]
        pad_x = int(OUT_W * 0.036)
        pad_y = int(OUT_W * 0.014)
        # 그림자 (살짝 아래)
        shadow_offset = 6
        draw.rectangle(
            [rx - pad_x, ry + shadow_offset - pad_y, rx + rw + pad_x, ry + shadow_offset + rh + pad_y],
            fill="#000000",
        )
        draw.rectangle(
            [rx - pad_x, ry - pad_y, rx + rw + pad_x, ry + rh + pad_y],
            fill=c_ribbon,
        )
        draw.text((rx - bbox[0], ry - bbox[1]), ribbon, font=rfont, fill=COLOR_WHITE)

    # 4. 메인 헤드라인 (좌측 띠 옆 + 위에서 30% 부근)
    # 좌측 노란 띠(SIDE_WIDTH)와 우측 8% 여백을 빼고 사용 가능 폭 계산.
    head_x = int(OUT_W * 0.10)
    avail_w = OUT_W - head_x - int(OUT_W * 0.04)
    head_y = int(OUT_H * 0.30)
    # prefix(지역명) — 폭 맞춰 자동 축소.
    if headline_prefix:
        pfont = _fit_font(headline_prefix, avail_w, HEAD_LINE_FONT_PX)
        _stroke_text(draw, (head_x, head_y), headline_prefix, pfont, COLOR_WHITE, COLOR_BLACK, 6)
        pbbox = pfont.getbbox(headline_prefix)
        head_y += int((pbbox[3] - pbbox[1]) * 1.20)
    # main(메인 키워드) — 폭 맞춰 자동 축소 + 노란 밑줄.
    mfont = _fit_font(headline_main, avail_w, HEAD_LINE_FONT_PX)
    bbox = draw.textbbox((0, 0), headline_main, font=mfont)
    mh = bbox[3] - bbox[1]
    mw = bbox[2] - bbox[0]
    underline_y = head_y + int(mh * 0.6) - bbox[1]
    underline_h = int(mh * 0.45)
    draw.rectangle(
        [head_x - bbox[0] - 4, underline_y, head_x - bbox[0] + mw + 8, underline_y + underline_h],
        fill=c_underline,
    )
    _stroke_text(draw, (head_x, head_y), headline_main, mfont, COLOR_WHITE, COLOR_BLACK, 6)

    # 5. 하단 검정 바 (사선 컷 흉내 — 간단히 직사각 + 위쪽 사선)
    bar_top = OUT_H - BAR_HEIGHT
    # 위쪽 사선을 위해 polygon
    skew = int(BAR_HEIGHT * 0.18)
    draw.polygon(
        [(0, bar_top + skew), (OUT_W, bar_top), (OUT_W, OUT_H), (0, OUT_H)],
        fill=c_bar,
    )

    # 5-1) tag (회색)
    tfont = _find_font(BAR_TAG_FONT_PX)
    tag_bbox = draw.textbbox((0, 0), tag, font=tfont)
    tag_x = (OUT_W - (tag_bbox[2] - tag_bbox[0])) // 2
    tag_y = bar_top + int(BAR_HEIGHT * 0.30)
    draw.text((tag_x, tag_y), tag, font=tfont, fill=COLOR_GRAY)

    # 5-2) brand: 노란 이름 · 분홍 점 · 흰 전화번호
    bfont = _find_font(BAR_BRAND_FONT_PX)
    name_bbox = draw.textbbox((0, 0), brand_name, font=bfont)
    phone_bbox = draw.textbbox((0, 0), phone, font=bfont)
    gap = int(OUT_W * 0.03)
    dot_r = int(OUT_W * 0.008)
    total_w = (name_bbox[2] - name_bbox[0]) + gap + dot_r * 2 + gap + (phone_bbox[2] - phone_bbox[0])
    bx = (OUT_W - total_w) // 2
    by = bar_top + int(BAR_HEIGHT * 0.60)
    # name
    draw.text((bx, by), brand_name, font=bfont, fill=COLOR_YELLOW)
    bx += (name_bbox[2] - name_bbox[0]) + gap
    # dot
    cy = by + (name_bbox[3] - name_bbox[1]) // 2
    draw.ellipse([bx, cy - dot_r, bx + dot_r * 2, cy + dot_r], fill=COLOR_PINK)
    bx += dot_r * 2 + gap
    # phone
    draw.text((bx, by), phone, font=bfont, fill=COLOR_WHITE)

    # 6. JPEG bytes 반환
    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def compose_for_site(
    domain: str,
    source_image_bytes: bytes,
    *,
    ribbon: str,
    headline_prefix: str,
    headline_main: str,
    tag: str = "24시 전국 배차 / 안전 책임 작업",
    brand_name: str = "아자스카이",
    phone: str = "010-9249-0510",
) -> bytes:
    """도메인별 OG 합성 디스패처. theme.og_config(domain) 으로 레이아웃·색을 골라
    hero/body 모든 호출이 같은 사이트 디자인을 쓰도록 한다."""
    from theme import og_config  # 지연 import (순환 회피)

    cfg = og_config(domain)
    if cfg.get("layout") == "panel":
        return compose_og_panel(
            source_image_bytes, ribbon=ribbon, headline_prefix=headline_prefix,
            headline_main=headline_main, tag=tag, brand_name=brand_name, phone=phone,
            accent=cfg.get("accent", "#2563eb"),
        )
    return compose_og(
        source_image_bytes, ribbon=ribbon, headline_prefix=headline_prefix,
        headline_main=headline_main, tag=tag, brand_name=brand_name, phone=phone,
        theme=cfg.get("theme"),
    )


def compose_og_panel(
    source_image_bytes: bytes,
    *,
    ribbon: str,           # 좌상 배지 (보드: "이용료")
    headline_prefix: str,  # 지역 ("고양시 가좌동")
    headline_main: str,    # 메인 키워드 ("스카이차")
    tag: str = "24시 전국 배차 / 안전 책임 작업",
    brand_name: str = "아자스카이",
    phone: str = "010-9249-0510",
    accent: str = "#2563eb",  # 배지·밑줄·브랜드 강조색
) -> bytes:
    """하단 패널형 구성. 사진을 크게 살리고 하단 그라데이션 패널에 텍스트.
    기존 시그니처(좌측 띠형)와 '같지만 다른' 레이아웃."""
    base = Image.open(BytesIO(source_image_bytes)).convert("RGB")
    base = _fit_center_crop(base, OUT_W, OUT_H)

    # 하단으로 갈수록 짙어지는 검정 그라데이션 (위쪽 사진은 선명하게 유지)
    grad = Image.new("L", (1, OUT_H), 0)
    start = int(OUT_H * 0.42)
    for y in range(start, OUT_H):
        t = (y - start) / (OUT_H - start)
        grad.putpixel((0, y), int(min(1.0, t * 1.15) * 236))
    grad = grad.resize((OUT_W, OUT_H))
    dark = Image.new("RGB", (OUT_W, OUT_H), (0, 0, 0))
    canvas = Image.composite(dark, base, grad)
    draw = ImageDraw.Draw(canvas)

    mL = int(OUT_W * 0.07)  # 좌측 여백

    # 1) 좌상 배지 (보드) — accent 박스 + 흰 글씨
    if ribbon:
        rfont = _find_font(int(OUT_W * 0.044))
        rb = draw.textbbox((0, 0), ribbon, font=rfont)
        rw, rh = rb[2] - rb[0], rb[3] - rb[1]
        px, py = int(OUT_W * 0.032), int(OUT_W * 0.018)
        bx0, by0 = mL, int(OUT_H * 0.06)
        draw.rounded_rectangle(
            [bx0, by0, bx0 + rw + px * 2, by0 + rh + py * 2],
            radius=int(OUT_W * 0.012), fill=accent,
        )
        draw.text((bx0 + px - rb[0], by0 + py - rb[1]), ribbon, font=rfont, fill=COLOR_WHITE)

    # 2) 하단 패널 텍스트 — 지역 → 키워드(밑줄) → 브랜드
    avail = OUT_W - mL - int(OUT_W * 0.07)

    # 지역 (아주 큰 글씨, 주인공) — 흰색 + 검정 외곽선으로 또렷하게
    pfont = _fit_font(headline_prefix, avail, int(OUT_W * 0.175), min_size=80)
    pb = pfont.getbbox(headline_prefix)
    ph = pb[3] - pb[1]
    # 키워드 (지역보다 작게, accent 밑줄로 강조 유지)
    mfont = _fit_font(headline_main, avail, int(OUT_W * 0.10), min_size=56)
    mb = mfont.getbbox(headline_main)
    mh = mb[3] - mb[1]

    # 브랜드 줄 폰트
    bfont = _find_font(int(OUT_W * 0.038))
    nb = draw.textbbox((0, 0), brand_name, font=bfont)
    fb = draw.textbbox((0, 0), phone, font=bfont)

    # 세로 배치: 아래에서부터 쌓기
    brand_y = int(OUT_H * 0.90)
    main_y = brand_y - int(mh * 1.18) - int(OUT_W * 0.045)
    prefix_y = main_y - int(ph * 1.28)

    # 지역 (큰 글씨 + 외곽선)
    _stroke_text(draw, (mL - pb[0], prefix_y - pb[1]), headline_prefix, pfont,
                 COLOR_WHITE, COLOR_BLACK, 6)
    # 키워드 + accent 밑줄
    mw = mb[2] - mb[0]
    uy = main_y + mh + int(OUT_W * 0.012)
    draw.rectangle([mL, uy, mL + min(mw, avail), uy + int(OUT_W * 0.014)], fill=accent)
    _stroke_text(draw, (mL - mb[0], main_y - mb[1]), headline_main, mfont, COLOR_WHITE, COLOR_BLACK, 4)
    # 브랜드: 이름(accent) · 점 · 전화(흰)
    draw.text((mL, brand_y), brand_name, font=bfont, fill=accent)
    bx = mL + (nb[2] - nb[0]) + int(OUT_W * 0.025)
    dot_r = int(OUT_W * 0.007)
    cy = brand_y + (nb[3] - nb[1]) // 2
    draw.ellipse([bx, cy - dot_r, bx + dot_r * 2, cy + dot_r], fill=accent)
    bx += dot_r * 2 + int(OUT_W * 0.025)
    draw.text((bx, brand_y), phone, font=bfont, fill=COLOR_WHITE)

    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def _fit_center_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    sw, sh = img.size
    target_ratio = target_w / target_h
    src_ratio = sw / sh
    if src_ratio > target_ratio:
        new_w = int(sh * target_ratio)
        x0 = (sw - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, sh))
    else:
        new_h = int(sw / target_ratio)
        y0 = (sh - new_h) // 2
        img = img.crop((0, y0, sw, y0 + new_h))
    return img.resize((target_w, target_h), Image.LANCZOS)
