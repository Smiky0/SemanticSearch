import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';
import { BACKEND, READ_ONLY_ENDPOINTS } from './lib/config.js';
import { resolveRepoId } from './lib/helpers.js';

// Hold steady foreground traffic while a large repo indexes in the background.
// Indexing is a BackgroundTask in the single worker process, so any blocking
// call in it starves every in-flight request. This is the test that catches it.

const foregroundMs = new Trend('foreground_ms', true);
const foregroundOk = new Rate('foreground_ok');
const healthOk = new Rate('health_ok');
// Percentiles missed the original outage: p95 was 144ms (PASS) while the
// server was dead for 13 minutes. These two counters caught it.
const blocked = new Counter('blocked_requests');
const overBudget = new Rate('over_budget_rate');
const budgetMs = Number(__ENV.REQUEST_BUDGET_MS || 5000);

const DURATION = __ENV.DURATION || '4m';
const VUS = Number(__ENV.VUS || 3);
const REPO_TO_INDEX = __ENV.INDEX_PATH || '/host/projects/devcart';
const RESET_REPO = (__ENV.RESET_REPO || 'true') !== 'false';

export const options = {
  scenarios: {
    foreground: {
      executor: 'constant-vus',
      vus: VUS,
      duration: DURATION,
      exec: 'foreground',
      gracefulStop: '30s',
    },
    indexer: {
      executor: 'shared-iterations',
      vus: 1,
      iterations: 1,
      startTime: __ENV.INDEX_START || '45s',
      maxDuration: '10m',
      exec: 'triggerIndex',
    },
  },
  thresholds: {
    // Hard availability gates. Indexing must not take the API down.
    blocked_requests: ['count==0'],
    over_budget_rate: ['rate<0.01'],
    // max catches a fully blocked event loop that p95 alone can miss.
    foreground_ms: [
      `p(95)<${__ENV.T_FG_P95 || 5000}`,
      `max<${__ENV.T_FG_MAX || 15000}`,
    ],
    foreground_ok: ['rate>0.99'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

// Phase marker so the summary can be read against a timeline.
const phase = __ENV.TAG_PREFIX ? `${__ENV.TAG_PREFIX}: ` : '';

export function setup() {
  const repoId = resolveRepoId();
  console.log(`contention: ${VUS} foreground VUs for ${DURATION}, indexing ${REPO_TO_INDEX} at t+${__ENV.INDEX_START || '45s'}`);
  return { repoId };
}

export function triggerIndex() {
  console.log(`${phase}>>> TRIGGERING INDEX of ${REPO_TO_INDEX}`);

  // An already-indexed path returns 409 and never schedules the task,
  // so a repeat run would be a silent no-op. Clear it first.
  if (RESET_REPO) {
    const repos = http.get(`${BACKEND}/api/repositories`, { timeout: '30s' });
    if (repos.status === 200) {
      const list = repos.json();
      const existing = (Array.isArray(list) ? list : []).find((r) => r.path === REPO_TO_INDEX);
      if (existing) {
        const del = http.del(`${BACKEND}/api/repositories/${existing.id}`, { timeout: '120s' });
        console.log(`${phase}deleted existing repo ${existing.id} -> ${del.status}`);
      }
    }
  }

  const res = http.post(
    `${BACKEND}/api/repositories/index`,
    JSON.stringify({ path: REPO_TO_INDEX }),
    { headers: { 'Content-Type': 'application/json' }, timeout: '60s' }
  );
  console.log(`${phase}index request -> ${res.status} in ${res.timings.duration.toFixed(0)}ms`);
  check(res, {
    'index accepted (200, or 409 when the path is already indexing)': () =>
      res.status === 200 || res.status === 409,
  });
}

export function foreground(data) {
  for (const ep of READ_ONLY_ENDPOINTS) {
    const res = http.get(`${BACKEND}${ep.path(data.repoId)}`, {
      timeout: '30s',
      tags: { endpoint: ep.name, phase: phase.trim() },
    });
    foregroundMs.add(res.timings.duration, { endpoint: ep.name });
    const dur = res.timings.duration;
    overBudget.add(dur > budgetMs, { endpoint: ep.name });
    if (res.status === 0) {
      blocked.add(1, { endpoint: ep.name });
      console.error(`${phase}BLOCKED ${ep.name} (connection not established in 30s)`);
    }
    const ok = res.status === 200;
    foregroundOk.add(ok, { endpoint: ep.name });
    check(res, { [`${ep.name}: 200`]: () => ok });
  }

  const h = http.get(`${BACKEND}/health`, { timeout: '30s', tags: { endpoint: 'GET /health' } });
  healthOk.add(h.status === 200);
  foregroundMs.add(h.timings.duration, { endpoint: 'GET /health' });
  overBudget.add(h.timings.duration > budgetMs, { endpoint: 'GET /health' });
  if (h.status === 0) {
    blocked.add(1, { endpoint: 'GET /health' });
    console.error(`${phase}BLOCKED GET /health (30s timeout)`);
  }

  sleep(0.5);
}
