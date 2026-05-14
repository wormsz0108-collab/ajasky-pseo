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
) -> bytes:
    # 1. 본 사진을 1080×1080으로 크롭/리사이즈 + 어둡게
    base = Image.open(BytesIO(source_image_bytes)).convert("RGB")
    base = _fit_center_crop(base, OUT_W, OUT_H)
    # 어두운 오버레이 (0.78 brightness 효과)
    dark = Image.new("RGB", (OUT_W, OUT_H), (0, 0, 0))
    base = Image.blend(base, dark, 0.22)

    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)

    # 2. 좌측 노란 세로 띠
    draw.rectangle([0, 0, SIDE_WIDTH, OUT_H], fill=COLOR_YELLOW)

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
            fill=COLOR_PINK,
        )
        draw.text((rx - bbox[0], ry - bbox[1]), ribbon, font=rfont, fill=COLOR_WHITE)

    # 4. 메인 헤드라인 (좌측 띠 옆 + 위에서 30% 부근)
    hfont = _find_font(HEAD_LINE_FONT_PX)
    head_x = int(OUT_W * 0.10)
    head_y = int(OUT_H * 0.30)
    if headline_prefix:
        _stroke_text(draw, (head_x, head_y), headline_prefix, hfont, COLOR_WHITE, COLOR_BLACK, 6)
        head_y += int(HEAD_LINE_FONT_PX * 1.05)
    # main에 노란 밑줄 박스 효과 (60% 위치부터 노란 배경)
    bbox = draw.textbbox((0, 0), headline_main, font=hfont)
    mh = bbox[3] - bbox[1]
    mw = bbox[2] - bbox[0]
    underline_y = head_y + int(mh * 0.6) - bbox[1]
    underline_h = int(mh * 0.45)
    draw.rectangle(
        [head_x - bbox[0] - 4, underline_y, head_x - bbox[0] + mw + 8, underline_y + underline_h],
        fill=COLOR_YELLOW,
    )
    _stroke_text(draw, (head_x, head_y), headline_main, hfont, COLOR_WHITE, COLOR_BLACK, 6)

    # 5. 하단 검정 바 (사선 컷 흉내 — 간단히 직사각 + 위쪽 사선)
    bar_top = OUT_H - BAR_HEIGHT
    # 위쪽 사선을 위해 polygon
    skew = int(BAR_HEIGHT * 0.18)
    draw.polygon(
        [(0, bar_top + skew), (OUT_W, bar_top), (OUT_W, OUT_H), (0, OUT_H)],
        fill=COLOR_BLACK,
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
