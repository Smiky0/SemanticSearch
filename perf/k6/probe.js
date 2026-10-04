import http from 'k6/http';
import { check } from 'k6';

// A shadowed or unreachable target must exit non-zero, otherwise a probe that
// detected the wrong application still reports success to the harness.
export const options = {
  vus: 1,
  iterations: 1,
  thresholds: { checks: ['rate==1'] },
};

// Diagnostic for BUG-011: a different service was once bound to host port
// 8000, so the k6 container could measure the wrong app without failing.
// Matching on the OpenAPI title proves which app answered.

const APP_TITLE = 'Semantic Code Search';

function identify(url) {
  const r = http.get(url + '/openapi.json', { timeout: '15s' });
  let title = null;
  try {
    title = JSON.parse(r.body).info && JSON.parse(r.body).info.title;
  } catch (e) {
    title = null;
  }
  return { status: r.status, title: title, body: String(r.body).slice(0, 100) };
}

export default function () {
  const containerUrl = __ENV.BASE_URL;
  const hostUrl = 'http://host.docker.internal:8000';

  const targets = [
    ['container ' + containerUrl + '/health', containerUrl + '/health'],
    ['container ' + containerUrl + '/api/repositories', containerUrl + '/api/repositories'],
    ['host     ' + hostUrl + '/health', hostUrl + '/health'],
    ['host     ' + hostUrl + '/api/repositories', hostUrl + '/api/repositories'],
  ];

  let shadowed = false;

  for (const [label, url] of targets) {
    // Accept 404 as "reachable but not this app" so the shadowing case is not
    // reported as a transport failure.
    const r = http.get(url, { timeout: '15s', responseCallback: http.expectedStatuses(200, 404, 502, 503) });
    const isApp = r.status === 200;
    console.log(
      `${String(r.status).padEnd(4)}${label.padEnd(58)}dur=${r.timings.duration.toFixed(1).padStart(7)}ms  ${String(r.body).slice(0, 90)}`
    );
    check(r, { [`${label}: reachable`]: () => r.status !== 0 });
    if (label.startsWith('host') && r.status !== 200) shadowed = true;
  }

  const container = identify(containerUrl);
  const host = identify(hostUrl);

  console.log('');
  console.log(`container network title: ${container.title}   (status ${container.status})`);
  console.log(`host published port title: ${host.title}   (status ${host.status})`);

  check(null, {
    'container target serves the expected app': () => container.title === APP_TITLE,
    'host port serves the expected app': () => host.title === APP_TITLE,
  });

  if (shadowed || host.title !== APP_TITLE) {
    console.log('');
    console.log('BUG-011 RECURRED: host port 8000 is not this application.');
    console.log('Another service is bound to host port 8000. Use BASE_URL=http://backend:8000.');
  } else {
    console.log('');
    console.log('BUG-011 CLEARED: container network and host port both serve ' + APP_TITLE + '.');
  }
}