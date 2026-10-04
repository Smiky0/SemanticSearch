import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { SEARCH_QUERIES, THRESHOLDS } from './lib/config.js';
import {
  DEFAULT_PARAMS,
  post,
  resolveRepoId,
  searchLatency,
  resultCount,
  emptyResults,
  blockedRequests,
  nonOkResponses,
} from './lib/helpers.js';

// Primary load test: POST /api/search. The most expensive request the backend
// serves - one embedding call, one Qdrant query, then a lookup per hit.

const success = new Rate('search_success');
const serverErrors = new Rate('search_server_error');
const searchMs = new Trend('search_ms', true);

const STAGES = (__ENV.STAGES || '30s:5,1m:15,2m:30,1m:30,30s:5').split(',').map((s) => {
  const [t, v] = s.split(':');
  return { duration: t.trim(), target: Number(v) };
});

export const options = {
  scenarios: {
    search: { executor: 'ramping-vus', stages: STAGES, gracefulRampDown: '15s' },
  },
  thresholds: {
    search_success: ['rate>0.98'],
    search_ms: [`p(95)<${THRESHOLDS.search.p95}`],
    http_req_failed: [`rate<${THRESHOLDS.errorRate}`],
    blocked_requests: ['count==0'],
    dropped_iterations: ['count==0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
  noConnectionReuse: false,
};

export function setup() {
  const repoId = resolveRepoId();
  if (!repoId) throw new Error('no indexed repository found — run the index step first');
  console.log(`search load -> repository ${repoId}`);
  return { repoId };
}

export default function (data) {
  const query = SEARCH_QUERIES[Math.floor(Math.random() * SEARCH_QUERIES.length)];
  const limit = Number(__ENV.LIMIT || 10);

  const res = post(
    '/api/search',
    { repository_id: data.repoId, query, limit },
    DEFAULT_PARAMS,
    { endpoint: 'POST /api/search' }
  );

  const dur = res.timings.duration;
  searchMs.add(dur, { endpoint: 'POST /api/search' });
  searchLatency.add(dur);

  if (res.status === 0) {
    blockedRequests.add(1, { endpoint: 'POST /api/search' });
  }

  const isOk = res.status === 200;
  success.add(isOk);
  nonOkResponses.add(isOk ? 0 : 1, { endpoint: 'POST /api/search', status: res.status });
  serverErrors.add(res.status >= 500);

  if (isOk) {
    const results = res.json('results') || [];
    resultCount.add(results.length);
    if (results.length === 0) emptyResults.add(1);
    check(res, { 'search: non-empty results': () => results.length > 0 });
    check(res, { 'search: results have score': () => results.every((r) => r.score !== undefined) });
  } else if (res.status !== 0) {
    console.error(`search ${res.status} q="${query}" body=${String(res.body).slice(0, 200)}`);
  }

  sleep(Number(__ENV.THINK_TIME || 0.2));
}
