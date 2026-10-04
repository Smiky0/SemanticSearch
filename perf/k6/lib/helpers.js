import http from 'k6/http';
import exec from 'k6/execution';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';
import { BACKEND, JSON_HEADERS, REPO_PATH } from './config.js';

// Custom metrics. The default http_req_* metrics lose the distinction between
// a fast 200 and a slow 200, which is exactly what we care about here.
export const searchLatency = new Trend('search_latency', true);
export const embedLatency = new Trend('embed_latency', true);
export const resultCount = new Trend('search_result_count');
export const emptyResults = new Counter('search_empty_results');
export const blockedRequests = new Counter('blocked_requests');
export const nonOkResponses = new Counter('non_ok_responses');

// http.get only takes (url, params), so tags have to ride inside params.tags.
// A third argument is silently dropped and you lose per-endpoint attribution.
export function get(url, params, tags) {
  const p = params || {};
  if (tags) p.tags = Object.assign({}, p.tags || {}, tags);
  return http.get(`${BACKEND}${url}`, p);
}

export function post(url, body, params, tags) {
  const p = params || {};
  p.headers = Object.assign({}, JSON_HEADERS, p.headers || {});
  if (tags) p.tags = Object.assign({}, p.tags || {}, tags);
  return http.post(`${BACKEND}${url}`, JSON.stringify(body), p);
}

// Deliberately long: we want to see the server degrade, not hide it behind
// client-side aborts.
export const DEFAULT_PARAMS = {
  timeout: '30s',
  tags: { timeout: '30s' },
};

export function expectOk(res, name, expectedStatus) {
  const want = expectedStatus || 200;
  const ok = res.status === want;
  check(res, { [`${name}: status ${want}`]: () => ok });
  if (!ok) {
    nonOkResponses.add(1, { endpoint: name, status: res.status });
  }
  return ok;
}

// Detects a stalled socket (k6 reports status 0 when the request could not be
// completed). These are the requests that would hang a real user.
export function expectNotBlocked(res, name) {
  const blocked = res.status === 0;
  check(res, { [`${name}: connection established`]: () => !blocked });
  if (blocked) {
    blockedRequests.add(1, { endpoint: name });
  }
  return !blocked;
}

// Resolves the repository under test once per test run. Retries because the
// API can still be settling immediately after a container restart.
export function resolveRepoId() {
  const wanted = __ENV.REPO_ID;
  if (wanted) return wanted;

  for (let attempt = 1; attempt <= 5; attempt += 1) {
    const res = get('/api/repositories', { timeout: '30s' });
    if (res.status === 200) {
      const body = res.json('repositories') || res.json() || [];
      const list = Array.isArray(body) ? body : body.repositories || [];
      const completed = list.filter(
        (r) => String(r.status).toLowerCase() === 'completed'
      );
      const preferred = completed.find((r) => r.path === REPO_PATH);
      const chosen = preferred || completed[0] || list[0];
      if (chosen) {
        console.log(`resolved repository ${chosen.id} (${chosen.path}, ${chosen.symbol_count} symbols)`);
        return chosen.id;
      }
    }
    console.warn(`resolveRepoId attempt ${attempt}/5 got status ${res.status}`);
    sleep(2 * attempt);
  }
  return null;
}

export function vus() {
  return exec.vu.idInTest;
}
