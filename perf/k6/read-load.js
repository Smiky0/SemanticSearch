import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { READ_ONLY_ENDPOINTS, THRESHOLDS } from './lib/config.js';
import { DEFAULT_PARAMS, get, resolveRepoId, blockedRequests } from './lib/helpers.js';

// Read-only load: cheap endpoints only (no embedding, no LLM).
// Establishes the FastAPI + Postgres + Qdrant-read baseline, so any regression
// seen in search-load can be attributed to the embedding path rather than the
// framework itself.

const success = new Rate('read_success');
const readMs = new Trend('read_ms', true);

const STAGES = (__ENV.STAGES || '30s:10,1m:25,2m:50,1m:25,30s:10').split(',').map((s) => {
  const [t, v] = s.split(':');
  return { duration: t.trim(), target: Number(v) };
});

export const options = {
  scenarios: {
    read: { executor: 'ramping-vus', stages: STAGES, gracefulRampDown: '15s' },
  },
  thresholds: {
    read_success: ['rate>0.99'],
    read_ms: [`p(95)<${THRESHOLDS.read.p95}`],
    http_req_failed: [`rate<${THRESHOLDS.errorRate}`],
    blocked_requests: ['count==0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  const repoId = resolveRepoId();
  console.log(`read load -> repository ${repoId}`);
  return { repoId };
}

export default function (data) {
  for (const ep of READ_ONLY_ENDPOINTS) {
    const path = ep.path(data.repoId);
    const params = Object.assign({}, DEFAULT_PARAMS);
    const res = get(path, params, { endpoint: ep.name });

    readMs.add(res.timings.duration, { endpoint: ep.name });
    if (res.status === 0) blockedRequests.add(1, { endpoint: ep.name });

    const ok = res.status === 200;
    success.add(ok, { endpoint: ep.name });
    check(res, { [`${ep.name}: 200`]: () => ok });
  }

  sleep(Number(__ENV.THINK_TIME || 0.2));
}
