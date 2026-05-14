"""본 이미지 121장 풀에서 글 slug 기반 결정적 선택.

같은 slug → 같은 이미지 (재시도/재발행에도 안정적).
다른 slug → 분산 (해시 기반).
"""
from __future__ import annotations

import hashlib

POOL_SIZE = 121


def pick_photo_key(slug: str) -> str:
    """slug → photos/NNN.jpg 키. NNN은 001~121."""
    h = hashlib.sha256(slug.encode("utf-8")).digest()
    n = int.from_bytes(h[:8], "big") % POOL_SIZE + 1
    return f"photos/{n:03d}.jpg"
