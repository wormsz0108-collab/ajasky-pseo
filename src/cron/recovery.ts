import type { Env } from '../types';

const DAILY_TARGET = 50;   // 네이버 일일 색인 요청 한도 50과 맞춤
const REPO = 'wormsz0108-collab/ajasky-pseo';
const BRANCH = 'master';
const MIN_GAP_TO_DISPATCH = 3;
const MAX_BATCH = 10;

export async function recoveryCron(env: Env): Promise<void> {
  const now = new Date();
  const hourUtc = now.getUTCHours();
  const todayUtcStart = new Date(Date.UTC(
    now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()
  )).toISOString();

  const target = Math.floor((hourUtc + 1) * DAILY_TARGET / 24);

  const row = await env.DB.prepare(
    `SELECT COUNT(*) as c FROM posts
     WHERE published_at >= ? AND status = 'published'`
  ).bind(todayUtcStart).first<{ c: number }>();
  const actual = row?.c ?? 0;
  const gap = target - actual;

  console.log(`[recovery] hour=${hourUtc} target=${target} actual=${actual} gap=${gap}`);

  if (gap < MIN_GAP_TO_DISPATCH) {
    console.log('[recovery] gap too small, skip');
    return;
  }

  // GHA에 이미 실행 중/대기 중 run 있으면 dispatch 안 함 (중복 방지)
  const activeRuns = await countActiveRuns(env);
  if (activeRuns > 0) {
    console.log(`[recovery] ${activeRuns} active run(s), skip`);
    return;
  }

  const batchSize = Math.min(MAX_BATCH, gap);
  await dispatchWorkflow(env, batchSize);
}

async function countActiveRuns(env: Env): Promise<number> {
  // GitHub IP rate limit 회피 위해 인증 헤더 포함 (Actions read 권한)
  const statuses = ['in_progress', 'queued'];
  let total = 0;
  for (const status of statuses) {
    const resp = await fetch(
      `https://api.github.com/repos/${REPO}/actions/workflows/publish.yml/runs?per_page=5&status=${status}`,
      {
        headers: {
          'Authorization': `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
          'User-Agent': 'ajasky-recovery',
          'Accept': 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
        },
      }
    );
    if (!resp.ok) {
      console.error(`[recovery] runs API (${status}) failed: ${resp.status}`);
      // 401/403이면 dispatch도 어차피 실패할 테니 막고, 5xx면 일단 시도 허용
      return resp.status >= 500 ? 0 : 999;
    }
    const data = await resp.json() as { workflow_runs: unknown[] };
    total += data.workflow_runs.length;
  }
  return total;
}

async function dispatchWorkflow(env: Env, batchSize: number): Promise<void> {
  const resp = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/publish.yml/dispatches`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'ajasky-recovery',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: BRANCH,
        inputs: {
          force_run: 'true',
          batch_size: String(batchSize),
        },
      }),
    }
  );

  if (resp.status === 204) {
    console.log(`[recovery] dispatched batch=${batchSize}`);
  } else {
    const text = await resp.text();
    console.error(`[recovery] dispatch failed: ${resp.status} ${text}`);
  }
}
