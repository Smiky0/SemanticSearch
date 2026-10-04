// Shared configuration for the Semantic Code Search k6 suite.
// All values can be overridden from the CLI with -e KEY=value.

const num = (v, d) => (v === undefined || v === '' ? d : Number(v));

// Default to the compose network service name. The published host port is
// unreliable: a local process on the same port wins the bind and the suite
// silently measures the wrong app (this happened once, see BUG-011).
export const BACKEND = __ENV.BASE_URL || 'http://backend:8000';
export const FRONTEND = __ENV.FRONTEND_URL || 'http://frontend';

// Repository under test. Auto-discovered in setup() when REPO_ID is absent.
export const REPO_ID = __ENV.REPO_ID || null;
export const REPO_PATH = __ENV.REPO_PATH || '/host/projects/Semantic-Code-Search';

// Absolute path to a second, larger corpus used to measure index throughput.
export const BIG_REPO_PATH = __ENV.BIG_REPO_PATH || null;

// Directory the browser endpoint is pointed at. Must exist inside the
// container, so it follows the compose mount rather than being hardcoded.
export const BROWSE_PATH = __ENV.BROWSE_PATH || '/host/projects';

export const JSON_HEADERS = { 'Content-Type': 'application/json' };

// Representative natural-language queries. Kept varied so Qdrant is not hit
// with a single cached-looking payload and the embedding path stays realistic.
export const SEARCH_QUERIES = [
  'where is authentication handled',
  'how are database connections created',
  'user model definition',
  'validate login credentials',
  'create a database session',
  'how does the search endpoint rank results',
  'where are embeddings generated',
  'error handling in the api layer',
  'repository indexing service',
  'how are symbols parsed from source files',
  'vector store upsert logic',
  'retry and backoff behaviour',
  'configuration settings loading',
  'graph edges between nodes',
  'how is a trace generated for a call chain',
];

// Lightweight, no-embedding endpoints. These isolate FastAPI/DB overhead from
// the embedding+vector search cost so regressions can be attributed.
export const READ_ONLY_ENDPOINTS = [
  { name: 'GET /health', method: 'GET', path: () => '/health' },
  { name: 'GET /api/repositories', method: 'GET', path: () => '/api/repositories' },
  {
    name: 'GET /api/repositories/{id}/status',
    method: 'GET',
    path: (r) => `/api/repositories/${r}/status`,
  },
  { name: 'GET /api/models', method: 'GET', path: () => '/api/models' },
  {
    name: 'GET /api/repositories/browse',
    method: 'GET',
    path: () => '/api/repositories/browse?path=/host/projects',
  },
  { name: 'GET /api/graph/{id}', method: 'GET', path: (r) => `/api/graph/${r}` },
];

export const THRESHOLDS = {
  health: { p95: num(__ENV.T_HEALTH_P95, 50) },
  read: { p95: num(__ENV.T_READ_P95, 500) },
  search: { p95: num(__ENV.T_SEARCH_P95, 5000) },
  errorRate: __ENV.T_ERROR_RATE || '0.01',
};
