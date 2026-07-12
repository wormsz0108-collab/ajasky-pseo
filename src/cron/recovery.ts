import type { Env } from '../types';

const REPO = 'wormsz0108-collab/ajasky-pseo';
const BRANCH = 'master';
const MIN_GAP_TO_DISPATCH = 3;
const MAX_BATCH = 10;

// 사이트별 복구 설정. 도메인별 네이버 색인 한도(50/일)가 따로라 각 사이트 목표를 독립으로 둔다.
// 한 사이트가 굶어도 다른 사이트 글이 갭을 가리지 않도록, 카운트/dispatch 모두 사이트 단위로 분리.
const SITE_CONFIGS = [
  { domain: 'ajasky.co.kr',  workflow: 'publish.yml',         dailyTarget: 50 },
  { domain: 'wormsz1.store', workflow: 'publish-wormsz1.yml', dailyTarget: 50 },
] as const;

type SiteConfig = (typeof SITE_CONFIGS)[number];

export async function recoveryCron(env: Env): Promise<void> {
  const now = new Date();
  const hourUtc = now.getUTCHours();
  const todayUtcStart = new Date(Date.UTC(
    now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()
  )).toISOString();

  // 사이트마다 독립적으로 갭 계산 → 부족하면 그 사이트 워크플로만 dispatch
  for (const site of SITE_CONFIGS) {
    await recoverSite(env, site, hourUtc, todayUtcStart);
  }
}

async function recoverSite(
  env: Env,
  site: SiteConfig,
  hourUtc: number,
  todayUtcStart: string,
): Promise<void> {
  const target = Math.floor((hourUtc + 1) * site.dailyTarget / 24);

  // 해당 사이트 글만 카운트 (site_id 필터) — 두 사이트 합산 버그 방지
  const row = await env.DB.prepare(
    `SELECT COUNT(*) as c FROM posts
     WHERE published_at >= ? AND status = 'published'
       AND site_id = (SELECT id FROM sites WHERE domain = ?)`
  ).bind(todayUtcStart, site.domain).first<{ c: number }>();
  const actual = row?.c ?? 0;
  const gap = target - actual;

  console.log(`[recovery] ${site.domain} hour=${hourUtc} target=${target} actual=${actual} gap=${gap}`);

  if (gap < MIN_GAP_TO_DISPATCH) {
    console.log(`[recovery] ${site.domain} gap too small, skip`);
    return;
  }

  // GHA에 해당 사이트 워크플로 run이 이미 실행 중/대기 중이면 dispatch 안 함 (중복 방지)
  const activeRuns = await countActiveRuns(env, site.workflow);
  if (activeRuns > 0) {
    console.log(`[recovery] ${site.domain} ${activeRuns} active run(s), skip`);
    return;
  }

  // gap-2 안전마진: 직후 도래할 schedule cron 과 겹쳐 일 페이스(50건)를 초과 발행하던
  // race 완화 (실측: recovery dispatch 와 schedule run 이 13초 간격 동시 실행된 이력).
  const batchSize = Math.min(MAX_BATCH, Math.max(1, gap - 2));
  await dispatchWorkflow(env, site, batchSize);
}

async function countActiveRuns(env: Env, workflow: string): Promise<number> {
  // GitHub IP rate limit 회피 위해 인증 헤더 포함 (Actions read 권한)
  const statuses = ['in_progress', 'queued'];
  let total = 0;
  for (const status of statuses) {
    const resp = await fetch(
      `https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/runs?per_page=5&status=${status}`,
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
      console.error(`[recovery] ${workflow} runs API (${status}) failed: ${resp.status}`);
      // 401/403이면 dispatch도 어차피 실패할 테니 막고, 5xx면 일단 시도 허용
      return resp.status >= 500 ? 0 : 999;
    }
    const data = await resp.json() as { workflow_runs: unknown[] };
    total += data.workflow_runs.length;
  }
  return total;
}

async function dispatchWorkflow(env: Env, site: SiteConfig, batchSize: number, retried = false): Promise<void> {
  const headers = {
    'Authorization': `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'ajasky-recovery',
  };
  const resp = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${site.workflow}/dispatches`,
    {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
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
    console.log(`[recovery] ${site.domain} dispatched ${site.workflow} batch=${batchSize}`);
    return;
  }

  const text = await resp.text();
  // GitHub 은 60일 무활동 repo 의 schedule 워크플로를 자동 비활성화 — 그대로 두면
  // 발행이 소리 없이 전면 정지하고 dispatch 도 403 으로 막힌다. enable 후 1회 재시도.
  if (!retried && resp.status === 403 && /disabled/i.test(text)) {
    const en = await fetch(
      `https://api.github.com/repos/${REPO}/actions/workflows/${site.workflow}/enable`,
      { method: 'PUT', headers }
    );
    if (en.status === 204) {
      console.log(`[recovery] ${site.domain} workflow re-enabled, retrying dispatch`);
      return dispatchWorkflow(env, site, batchSize, true);
    }
    console.error(`[recovery] ${site.domain} workflow enable failed: ${en.status}`);
  }
  console.error(`[recovery] ${site.domain} dispatch failed: ${resp.status} ${text}`);
}
