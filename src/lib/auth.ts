// Bearer 토큰 검증 — 평문 토큰의 SHA-256과 wrangler secret 비교 (constant-time)

function hexToBytes(hex: string): Uint8Array {
  if (hex.length % 2 !== 0) return new Uint8Array(0);
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    out[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return out;
}

function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

export async function verifyBearer(authHeader: string | null, expectedHashHex: string): Promise<boolean> {
  if (!authHeader || !authHeader.startsWith('Bearer ')) return false;
  const token = authHeader.slice('Bearer '.length).trim();
  if (!token) return false;
  const data = new TextEncoder().encode(token);
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', data));
  const expected = hexToBytes(expectedHashHex);
  return timingSafeEqual(digest, expected);
}
