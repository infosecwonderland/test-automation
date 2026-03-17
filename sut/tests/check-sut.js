const http = require('http');

const BASE_URL = process.env.SUT_BASE_URL || 'http://localhost:3000';

const apiEndpoints = [
  { method: 'POST', path: '/auth/login' },
  { method: 'GET', path: '/products' },
  { method: 'POST', path: '/cart/add' },
  { method: 'POST', path: '/order/create' },
  { method: 'POST', path: '/payment/charge' }
];

const pages = [
  '/login',
  '/products',
  '/cart',
  '/checkout',
  '/payment',
  '/order-confirmation'
];

function request(method, path, body) {
  return new Promise((resolve, reject) => {
    const url = new URL(BASE_URL + path);
    const payload = body ? JSON.stringify(body) : null;

    const options = {
      method,
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      headers: payload
        ? {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(payload)
          }
        : {}
    };

    const req = http.request(options, res => {
      let data = '';
      res.on('data', chunk => (data += chunk));
      res.on('end', () => {
        resolve({ status: res.statusCode, body: data });
      });
    });

    req.on('error', reject);

    if (payload) {
      req.write(payload);
    }
    req.end();
  });
}

async function main() {
  console.log(`Checking SUT at ${BASE_URL}`);

  const results = [];

  // Prepare a happy-path flow for APIs that depend on state
  let orderIdForPayment = null;

  // Check pages
  for (const path of pages) {
    try {
      const res = await request('GET', path);
      const ok = res.status === 200;
      results.push({ type: 'PAGE', path, ok, status: res.status });
    } catch (err) {
      results.push({ type: 'PAGE', path, ok: false, error: err.message });
    }
  }

  // Check APIs (basic positive/negative where possible)
  for (const ep of apiEndpoints) {
    try {
      let body = undefined;
      if (ep.path === '/auth/login') {
        body = { username: 'testuser', password: 'password123' };
      } else if (ep.path === '/cart/add') {
        body = { productId: 1, quantity: 1 };
      } else if (ep.path === '/order/create') {
        // assume cart already has item from previous call
        body = {};
      } else if (ep.path === '/payment/charge') {
        // use a real order from previous step if available
        body = { orderId: orderIdForPayment || 'non-existent', cardNumber: '4242424242424242' };
      }

      const res = await request(ep.method, ep.path, body);

      // Capture a valid order id for the payment step
      if (ep.path === '/order/create' && res.status === 201) {
        try {
          const parsed = JSON.parse(res.body || '{}');
          if (parsed.orderId) {
            orderIdForPayment = parsed.orderId;
          }
        } catch {
          // ignore JSON parse issues here
        }
      }

      // For structure check, require success (2xx) for all these core APIs
      const ok = res.status >= 200 && res.status < 300;
      results.push({
        type: 'API',
        method: ep.method,
        path: ep.path,
        ok,
        status: res.status
      });
    } catch (err) {
      results.push({
        type: 'API',
        method: ep.method,
        path: ep.path,
        ok: false,
        error: err.message
      });
    }
  }

  console.table(results);

  const allOk = results.every(r => r.ok);
  if (!allOk) {
    console.error('SUT structure check FAILED');
    process.exitCode = 1;
  } else {
    console.log('SUT structure check PASSED (all required APIs/pages reachable)');
  }
}

main().catch(err => {
  console.error('Error while checking SUT:', err);
  process.exitCode = 1;
});

