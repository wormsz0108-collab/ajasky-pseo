// 글 slug 기반 결정적 사진 선택. 121장 풀에서 hero(og)와 다른 2~3장 추출.
// 같은 글 = 같은 사진 (재방문 안정성).

const POOL_SIZE = 121;

function hash(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  return h;
}

export function pickBodyPhotos(slug: string, region: string, boardTitle: string): { url: string; caption: string }[] {
  const captions = [
    `${region} 현장 작업 모습`,
    `${region} ${boardTitle} 실제 진행 장면`,
    `${region} 일대 작업 사례`,
  ];
  const photos: { url: string; caption: string }[] = [];
  for (let i = 0; i < 3; i++) {
    const n = (hash(`${slug}#body${i}`) % POOL_SIZE) + 1;
    const key = `photos/${String(n).padStart(3, '0')}.jpg`;
    photos.push({ url: `/media/${key}`, caption: captions[i] });
  }
  return photos;
}
