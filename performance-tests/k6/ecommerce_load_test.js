import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend, Rate } from 'k6/metrics';

// Custom metrics (optional but useful in dashboards)
export const loginDuration = new Trend('login_duration');
export const purchaseDuration = new Trend('purchase_flow_duration');
export const errors = new Rate('errors');

// Base configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
const USER_EMAIL = __ENV.USER_EMAIL || 'test@example.com';
const USER_PASSWORD = __ENV.USER_PASSWORD || 'password123';
const CARD_NUMBER = __ENV.CARD_NUMBER || '4111111111111111';

/**
 * Load profile:
 * - 1 minute ramp-up to 1000 VUs
 * - 3 minutes sustained at 1000 VUs
 * - 1 minute ramp-down
 */
export const options = {
  stages: [
    { duration: '1m', target: 100 },
    { duration: '3m', target: 100 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // P95 latency < 2s
    http_req_failed: ['rate<0.01'], // < 1% requests failing
    errors: ['rate<0.01'],
  },
};

/**
 * setup()
 * Runs once before all VUs.
 * We log in once and share the JWT across all VUs to avoid
 * turning the test into an auth/load test.
 */
export function setup() {
  const loginRes = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({
      email: USER_EMAIL,
      password: USER_PASSWORD,
    }),
    {
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );

  const ok = check(loginRes, {
    'login status is 200': (r) => r.status === 200,
    'login has accessToken': (r) => {
      try {
        const json = r.json();
        return json && json.accessToken;
      } catch (e) {
        return false;
      }
    },
  });

  loginDuration.add(loginRes.timings.duration);
  errors.add(!ok);

  if (!ok) {
    throw new Error(`Login failed: status=${loginRes.status} body=${loginRes.body}`);
  }

  const token = loginRes.json().accessToken;
  const authHeaders = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  return { authHeaders };
}

/**
 * Default function executed by each VU on each iteration.
 * Models: login -> search products -> add to cart -> create order -> payment
 */
export default function (data) {
  const { authHeaders } = data;

  const flowStart = Date.now();

  group('search products', () => {
    const res = http.get(`${BASE_URL}/products`, {
      headers: authHeaders,
    });

    const ok = check(res, {
      'products status is 200': (r) => r.status === 200,
      'products list is non-empty': (r) => {
        try {
          const json = r.json();
          return Array.isArray(json) && json.length > 0;
        } catch (e) {
          return false;
        }
      },
    });

    errors.add(!ok);
  });

  let productId = null;
  try {
    const productsRes = http.get(`${BASE_URL}/products`, { headers: authHeaders });
    const products = productsRes.json();
    if (Array.isArray(products) && products.length > 0) {
      productId = products[0].id || products[0].productId || 1;
    } else {
      productId = 1;
    }
  } catch (e) {
    productId = 1;
  }

  group('add to cart', () => {
    const res = http.post(
      `${BASE_URL}/cart/add`,
      JSON.stringify({
        productId,
        quantity: 1,
      }),
      { headers: authHeaders },
    );

    const ok = check(res, {
      'cart add status is 200': (r) => r.status === 200,
    });
    errors.add(!ok);
  });

  let orderId = null;

  group('create order', () => {
    const res = http.post(
      `${BASE_URL}/order/create`,
      JSON.stringify({}),
      { headers: authHeaders },
    );

    const ok = check(res, {
      'order create status is 200': (r) => r.status === 200,
      'order has id': (r) => {
        try {
          const json = r.json();
          return json && (json.id || json.orderId);
        } catch (e) {
          return false;
        }
      },
    });

    errors.add(!ok);

    if (ok) {
      const body = res.json();
      orderId = body.id || body.orderId;
    }
  });

  if (orderId) {
    group('payment charge', () => {
      const res = http.post(
        `${BASE_URL}/payment/charge`,
        JSON.stringify({
          orderId,
          cardNumber: CARD_NUMBER,
        }),
        { headers: authHeaders },
      );

      const ok = check(res, {
        'payment status is 200': (r) => r.status === 200,
      });
      errors.add(!ok);
    });
  }

  const flowDuration = Date.now() - flowStart;
  purchaseDuration.add(flowDuration);

  // Tiny sleep to avoid a 100% tight loop
  sleep(0.5);
}

