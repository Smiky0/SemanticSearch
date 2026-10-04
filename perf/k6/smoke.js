import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter } from 'k6/metrics';
import { BACKEND, BROWSE_PATH } from './lib/config.js';

// Functional smoke test. Runs every endpoint once with a single VU to prove
// the contract before any load is applied. Run this first - if it fails,
// the load numbers are meaningless.

const failures = new Counter('smoke_failures');

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    smoke_failures: ['count==0'],
    http_req_failed: ['rate==0'],
  },
};

export function setup() {
  const res = http.get(`${BACKEND}/api/repositories`, { timeout: '30s' });
  if (res.status !== 200) return { repoId: null, repos: [] };
  const body = res.json('repositories') || res.json() || [];
  const repos = Array.isArray(body) ? body : [];
  const completed = repos.filter((r) => String(r.status).toUpperCase() === 'COMPLETED');
  const repo = completed[0] || repos[0] || null;
  return {
    repoId: repo ? repo.id : null,
    repos: repos.map((r) => ({ id: r.id, path: r.path, status: r.status, symbols: r.symbol_count })),
  };
}

function record(name, res, validate) {
  const ok = check(res, { [`${name} -> 200`]: () => res.status === 200 });
  if (!ok) {
    failures.add(1);
    console.error(`FAIL ${name} status=${res.status} body=${String(res.body).slice(0, 300)}`);
  } else if (validate) {
    const vok = validate(res);
    if (!vok) {
      failures.add(1);
      console.error(`FAIL ${name} body contract`);
    }
  }
  console.log(`ok   ${name} status=${res.status} dur=${res.timings.duration.toFixed(1)}ms`);
  return res;
}

export default function (data) {
  const j = { 'Content-Type': 'application/json' };
  const T = { timeout: '30s' };

  group('infrastructure', () => {
    record('GET /health', http.get(`${BACKEND}/health`, T), (r) => r.json('status') === 'ok');

    record(
      'GET /api/repositories',
      http.get(`${BACKEND}/api/repositories`, T),
      (r) => Array.isArray(r.json('repositories') || r.json()) || true
    );

    record(
      'GET /api/repositories/browse',
      http.get(`${BACKEND}/api/repositories/browse?path=${BROWSE_PATH}`, T),
      (r) => Array.isArray(r.json('entries'))
    );
  });

  group('configuration', () => {
    record('GET /api/config/providers', http.get(`${BACKEND}/api/config/providers`, T), (r) =>
      ['gemini', 'ollama'].includes(r.json('active_embedding'))
    );
    record('GET /api/models', http.get(`${BACKEND}/api/models`, T));
  });

  if (!data.repoId) {
    console.error('no indexed repository found — skipping repo-scoped checks');
    failures.add(1);
    return;
  }

  const id = data.repoId;
  console.log(`using repository ${id}`);

  group('repository scoped', () => {
    record('GET /api/repositories/{id}/status', http.get(`${BACKEND}/api/repositories/${id}/status`, T), (r) =>
      typeof r.json('status') === 'string'
    );

    const graph = record('GET /api/graph/{id}', http.get(`${BACKEND}/api/graph/${id}`, T), (r) =>
      Array.isArray(r.json('nodes'))
    );

    const nodes = (graph.json('nodes') || []).filter((n) => n.symbol_type !== 'FILE');
    if (!nodes.length) {
      console.error('no symbol nodes to probe');
      failures.add(1);
    } else {
      const sym = nodes[Math.floor(Math.random() * nodes.length)];
      record('GET /api/symbols/{id}', http.get(`${BACKEND}/api/symbols/${sym.id}`, T));
      record('GET /api/symbols/{id}/relationships', http.get(`${BACKEND}/api/symbols/${sym.id}/relationships`, T));
    }
  });

  group('semantic pipeline (slow path)', () => {
    record(
      'POST /api/search',
      http.post(`${BACKEND}/api/search`, JSON.stringify({ repository_id: id, query: 'where is authentication handled', limit: 10 }), { headers: j, timeout: '60s' }),
      (r) => Array.isArray(r.json('results')) && r.json('results').length > 0
    );

    // explain/trace hit the local LLM; 120s is the configured provider timeout.
    const explain = http.post(`${BACKEND}/api/explain`, JSON.stringify({ repository_id: id, query: 'where is authentication handled' }), { headers: j, timeout: '150s' });
    const eok = check(explain, { 'POST /api/explain -> 200': () => explain.status === 200 });
    console.log(`${eok ? 'ok  ' : 'FAIL'} POST /api/explain status=${explain.status} dur=${explain.timings.duration.toFixed(0)}ms`);
    if (!eok) {
      failures.add(1);
      console.error(`explain body=${String(explain.body).slice(0, 300)}`);
    }

    const trace = http.post(`${BACKEND}/api/trace`, JSON.stringify({ repository_id: id, query: 'how are database connections created' }), { headers: j, timeout: '150s' });
    const tok = check(trace, { 'POST /api/trace -> 200': () => trace.status === 200 });
    console.log(`${tok ? 'ok  ' : 'FAIL'} POST /api/trace status=${trace.status} dur=${trace.timings.duration.toFixed(0)}ms`);
    if (!tok) {
      failures.add(1);
      console.error(`trace body=${String(trace.body).slice(0, 300)}`);
    }
  });

  group('frontend proxy', () => {
    const fe = http.get(`${__ENV.FRONTEND_URL || 'http://host.docker.internal'}/`, { timeout: '30s' });
    const feok = check(fe, { 'GET / (nginx) -> 200': () => fe.status === 200 });
    console.log(`${feok ? 'ok  ' : 'FAIL'} GET / status=${fe.status}`);
    if (!feok) failures.add(1);
  });

  sleep(0.5);
}
