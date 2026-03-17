import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend, Rate } from 'k6/metrics';

// Custom metrics
export const loginDuration = new Trend('login_duration');
export const purchaseDuration = new Trend('purchase_flow_duration');
export const errors = new Rate('errors');

// Base configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
const CARD_NUMBER = __ENV.CARD_NUMBER || '4111111111111111';

/**
 * Load profile:
 * - 2 minutes ramp-up to 1000 VUs
 * - 3 minutes sustained at 1000 VUs
 * - 1 minute ramp-down
 */
export const options = {
  stages: [
    { duration: '2m', target: 1000 },
    { duration: '3m', target: 1000 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // P95 latency < 2s
    http_req_failed: ['rate<0.01'],    // < 1% requests failing
    errors: ['rate<0.01'],
  },
};

// VU-scoped auth state — module-level variables are isolated per VU in k6
let vuAuthHeaders = null;

/**
 * Authenticate this VU using a unique per-VU account.
 * Registers on first call (409 conflict is safe to ignore on re-runs),
 * then logs in and caches the token for the lifetime of the VU.
 */
function ensureAuth() {
  if (vuAuthHeaders) return;

  const email = `vu_${__VU}@perf.test`;
  const password = 'PerfTest123!';
  const jsonHeaders = { 'Content-Type': 'application/json' };

  // Register — ignore 409 (user already exists from a previous run)
  http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify({ email, password }),
    { headers: jsonHeaders },
  );

  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email, password }),
    { headers: jsonHeaders },
  );

  loginDuration.add(loginRes.timings.duration);

  const ok = check(loginRes, {
    'VU login status is 200': (r) => r.status === 200,
    'VU login has accessToken': (r) => {
      try { return !!r.json('accessToken'); } catch (e) { return false; }
    },
  });

  errors.add(!ok);

  if (!ok) {
    console.error(`VU ${__VU} login failed: ${loginRes.status} ${loginRes.body}`);
    return;
  }

  vuAuthHeaders = {
    Authorization: `Bearer ${loginRes.json('accessToken')}`,
    'Content-Type': 'application/json',
  };
}

/**
 * Default function executed by each VU on each iteration.
 * Flow: authenticate → search products → add to cart → create order → payment
 */
export default function () {
  ensureAuth();
  if (!vuAuthHeaders) return; // skip iteration if auth failed

  const flowStart = Date.now();
  let productId = 1;

  group('search products', () => {
    const res = http.get(`${BASE_URL}/products`, { headers: vuAuthHeaders });

    const ok = check(res, {
      'products status is 200': (r) => r.status === 200,
      'products list is non-empty': (r) => {
        try {
          const json = r.json();
          return Array.isArray(json) && json.length > 0;
        } catch (e) { return false; }
      },
    });

    errors.add(!ok);

    if (ok) {
      try {
        const products = res.json();
        // Rotate through products by VU index to spread load
        productId = products[(__VU - 1) % products.length].id;
      } catch (e) { /* fallback to productId = 1 */ }
    }
  });

  group('add to cart', () => {
    const res = http.post(
      `${BASE_URL}/cart/add`,
      JSON.stringify({ productId, quantity: 1 }),
      { headers: vuAuthHeaders },
    );

    const ok = check(res, {
      'cart add status is 201': (r) => r.status === 201,
    });
    errors.add(!ok);
  });

  let orderId = null;

  group('create order', () => {
    const res = http.post(
      `${BASE_URL}/order/create`,
      JSON.stringify({}),
      { headers: vuAuthHeaders },
    );

    const ok = check(res, {
      'order create status is 201': (r) => r.status === 201,
      'order has orderId': (r) => {
        try { return !!r.json('orderId'); } catch (e) { return false; }
      },
    });

    errors.add(!ok);

    if (ok) {
      try { orderId = res.json('orderId'); } catch (e) { /* skip payment */ }
    }
  });

  if (orderId) {
    group('payment charge', () => {
      const res = http.post(
        `${BASE_URL}/payment/charge`,
        JSON.stringify({ orderId, cardNumber: CARD_NUMBER }),
        { headers: vuAuthHeaders },
      );

      const ok = check(res, {
        'payment status is 200': (r) => r.status === 200,
        'payment status is PAID': (r) => {
          try { return r.json('status') === 'PAID'; } catch (e) { return false; }
        },
      });
      errors.add(!ok);
    });
  }

  purchaseDuration.add(Date.now() - flowStart);

  sleep(1);
}

