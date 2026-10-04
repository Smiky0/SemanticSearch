import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { SEARCH_QUERIES } from './lib/config.js';
import { DEFAULT_PARAMS, post, resolveRepoId, blockedRequests } from './lib/helpers.js';

// Spike test: sudden step change in load, then recovery.
// Answers "what happens when traffic arrives in a burst instead of a ramp?"
// We care about two things: does the service shed load gracefully (no 5xx
// storm) and how long does it take to recover to a healthy p95.

const success = new Rate('spike_success');
const spikeMs = new Trend('spike_ms', true);

const PEAK = Number(__ENV.PEAK_VUS || 100);
const HOLD = __ENV.HOLD || '2m';
const BASE = Number(__ENV.BASE_VUS || 5);

export const options = {
  scenarios: {
    spike: {
      executor: 'ramping-vus',
      startVUs: BASE,
      stages: [
        { duration: '30s', target: BASE }, // steady baseline
        { duration: '10s', target: PEAK }, // instant step to peak
        { duration: HOLD, target: PEAK }, // hold the peak
        { duration: '30s', target: BASE }, // drop back down
        { duration: '1m', target: BASE }, // observe recovery
      ],
      gracefulRampDown: '20s',
    },
  },
  thresholds: {
    spike_success: ['rate>0.90'],
    spike_ms: [`p(95)<${__ENV.T_SPIKE_P95 || 20000}`],
    blocked_requests: ['count==0'],
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  const repoId = resolveRepoId();
  if (!repoId) throw new Error('no indexed repository found');
  console.log(`spike ${BASE} -> ${PEAK} VUs for ${HOLD}`);
  return { repoId };
}

export default function (data) {
  const query = SEARCH_QUERIES[Math.floor(Math.random() * SEARCH_QUERIES.length)];
  const res = post(
    '/api/search',
    { repository_id: data.repoId, query, limit: 10 },
    Object.assign({}, DEFAULT_PARAMS, { timeout: '45s' }),
    { endpoint: 'POST /api/search' }
  );

  spikeMs.add(res.timings.duration);
  if (res.status === 0) blockedRequests.add(1);
  const ok = res.status === 200;
  success.add(ok);
  check(res, { 'spike: search 200': () => ok });

  sleep(0.1);
}
