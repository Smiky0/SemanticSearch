import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { SEARCH_QUERIES } from './lib/config.js';
import { DEFAULT_PARAMS, post, resolveRepoId, blockedRequests } from './lib/helpers.js';

// Soak / endurance test: sustained moderate load for a long window.
// A service can pass a 5-minute load test and still fail at 2 hours — this
// catches memory growth, connection-pool exhaustion and event-loop drift.
// Watch the per-minute table printed at the end: rising latency with flat
// throughput is the classic symptom.

const success = new Rate('soak_success');
const soakMs = new Trend('soak_ms', true);
const duration = __ENV.DURATION || '10m';
const vus = Number(__ENV.VUS || 10);

// Each minute gets its own untagged Trend (soak_minute_00, ...). Tagged
// sub-metrics are dropped by --summary-export and VU module state can't reach
// handleSummary, so only untagged top-level metrics survive. They have to be
// declared in the init context, hence the up-front list.
function durationSeconds(spec) {
  const text = String(spec).trim();
  const parts = /(\d+)([smh])/g;
  let total = 0;
  let consumed = 0;
  let match;
  while ((match = parts.exec(text)) !== null) {
    const n = Number(match[1]);
    total += match[2] === 'h' ? n * 3600 : match[2] === 'm' ? n * 60 : n;
    consumed += match[0].length;
  }
  return consumed > 0 && consumed === text.length ? total : 600;
}

const MAX_DRIFT_RATIO = Number(__ENV.MAX_DRIFT_RATIO || 2.0);

const minuteTrends = [];
const maxMinutes = Math.min(120, Math.floor(durationSeconds(duration) / 60) + 2);
for (let i = 0; i < maxMinutes; i++) {
  minuteTrends.push(new Trend(`soak_minute_${String(i).padStart(2, '0')}`, true));
}

let epochStart = null;

export const options = {
  scenarios: {
    soak: {
      executor: 'constant-vus',
      vus,
      duration,
      gracefulStop: '30s',
    },
  },
  thresholds: {
    // Strict: a soak test that only passes at 95% availability has found a bug.
    soak_success: ['rate>0.98'],
    soak_ms: [`p(95)<${__ENV.T_SOAK_P95 || 15000}`],
    blocked_requests: ['count==0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  const repoId = resolveRepoId();
  if (!repoId) throw new Error('no indexed repository found');
  console.log(`soak: ${vus} VUs for ${duration}`);
  return { repoId };
}

export default function (data) {
  const query = SEARCH_QUERIES[Math.floor(Math.random() * SEARCH_QUERIES.length)];
  const res = post(
    '/api/search',
    { repository_id: data.repoId, query, limit: 10 },
    DEFAULT_PARAMS,
    { endpoint: 'POST /api/search' }
  );

  const ms = res.timings.duration;
  soakMs.add(ms);

  if (epochStart === null) epochStart = Date.now();
  const minute = Math.floor((Date.now() - epochStart) / 60000);
  if (minute < minuteTrends.length) minuteTrends[minute].add(ms);

  if (res.status === 0) blockedRequests.add(1);
  const ok = res.status === 200;
  success.add(ok);
  check(res, { 'soak: search 200': () => ok });

  sleep(Number(__ENV.THINK_TIME || 0.3));
}

export function handleSummary(data) {
  const metrics = data.metrics || {};
  // In-memory summary entries are {type, contains, values:{...}}; k6 flattens
  // them only when writing --summary-export. Accept both shapes.
  const stat = (name, key) => {
    const e = metrics[name];
    if (!e) return undefined;
    const v = e.values || e;
    return v[key];
  };

  const rows = Object.keys(metrics)
    .filter((k) => /^soak_minute_\d+$/.test(k))
    .sort()
    .map((k) => ({
      minute: Number(k.slice('soak_minute_'.length)),
      mean_ms: Math.round(stat(k, 'avg')),
      p95_ms: Math.round(stat(k, 'p(95)')),
      max_ms: Math.round(stat(k, 'max')),
    }))
    .filter((r) => Number.isFinite(r.mean_ms));

  const line = (s) => `\n${s}`;
  let out = '';
  out += line('=== DRIFT (latency per elapsed minute) ===');
  for (const r of rows) {
    out += line(
      `  minute ${String(r.minute).padStart(2)}` +
        `  mean=${String(r.mean_ms).padStart(6)}ms  p95=${String(r.p95_ms).padStart(6)}ms` +
        `  max=${String(r.max_ms).padStart(7)}ms`
    );
  }

  let verdict = null;
  if (rows.length >= 3) {
    const third = Math.max(1, Math.floor(rows.length / 3));
    const firstMean = Math.round(rows.slice(0, third).reduce((a, r) => a + r.mean_ms, 0) / third);
    const lastMean = Math.round(rows.slice(-third).reduce((a, r) => a + r.mean_ms, 0) / third);
    const ratio = firstMean > 0 ? lastMean / firstMean : 1;
    verdict = {
      first_third_mean_ms: firstMean,
      last_third_mean_ms: lastMean,
      ratio: Number(ratio.toFixed(2)),
      max_drift_ratio: MAX_DRIFT_RATIO,
      pass: ratio <= MAX_DRIFT_RATIO,
    };
    out += line(`  first-third mean: ${firstMean}ms`);
    out += line(`  last-third  mean: ${lastMean}ms`);
    out += line(`  drift ratio: ${verdict.ratio}x (gate <=${MAX_DRIFT_RATIO}x)`);
    out += line(`  DRIFT VERDICT: ${verdict.pass ? 'PASS' : 'FAIL'}`);
  } else {
    out += line('  (need >=3 minute windows for a drift verdict; run >=3m)');
  }

  data.drift = { windows: rows, verdict: verdict };

  // --summary-export still writes `data`; this only reshapes stdout so the
  // drift table lands in the captured log next to the normal summary.
  return { stdout: out + '\n' + JSON.stringify(data, null, 2), stderr: '' };
}