const express = require('express');
const path = require('path');
const cors = require('cors');
const bodyParser = require('body-parser');
const jwt = require("jsonwebtoken");
const OpenApiValidator = require('express-openapi-validator');

const { createAuthRouter } = require('./services/auth');
const { createProductRouter } = require('./services/products');
const { createCartRouter } = require('./services/cart');
const { createOrderRouter } = require('./services/order');
const { createPaymentRouter } = require('./services/payment');
const { createKafkaBus } = require('./lib/kafka-bus');
const { createDb } = require('./lib/db');

// Keep JWT secret consistent with auth service
const JWT_SECRET = process.env.SUT_JWT_SECRET || 'sut-secret';
const JWT_EXPIRES_IN = "1h";
const PORT = process.env.SUT_PORT || process.env.PORT || 3000;

function createApp() {
  const app = express();

  app.use(cors());
  app.use(bodyParser.json());
  app.use(express.urlencoded({ extended: true }));

  const db = createDb();
  const kafka = createKafkaBus();

  function requireAuth(req, res, next) {
    const authHeader = req.headers.authorization || '';
    const [, token] = authHeader.split(' ');
    if (!token) {
      return res.status(401).json({ message: 'missing token' });
    }

    try {
      const payload = jwt.verify(token, JWT_SECRET);
      req.user = { id: payload.sub, email: payload.email };
      next();
    } catch (err) {
      return res.status(401).json({ message: 'invalid token' });
    }
  }



  // In-memory data for demo purposes
  const products = [
    { id: 1, name: 'Laptop', price: 1200 },
    { id: 2, name: 'Headphones', price: 200 },
    { id: 3, name: 'Phone', price: 800 }
  ];

  let carts = {};
  let orders = {};

  // API route for order details (must be before static so GET /order/:id is not shadowed)


  // ---- UI PAGES ----

  app.use(express.static(path.join(__dirname, 'public')));

  app.get('/', (req, res) => {
    res.redirect('/login');
  });

  // Explicit page routes (for clarity in tests)
  app.get('/login', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'login.html'));
  });

  app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'register.html'));
  });

  // UI route for products/search page (API uses /products)
  app.get('/products-page', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'products.html'));
  });

  app.get('/cart', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'cart.html'));
  });

  app.get('/checkout', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'checkout.html'));
  });

  app.get('/payment', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'payment.html'));
  });

  app.get('/order-confirmation', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'confirmation.html'));
  });

  // ---- OpenAPI validation for API routes ----

  // Middleware before OpenAPI validator to trace which paths reach it
  app.use((req, res, next) => {
    // #region agent log
    fetch('http://127.0.0.1:7720/ingest/83b26dc7-e0f6-447f-ae08-2bd6e4dc06c6', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': '50206d',
      },
      body: JSON.stringify({
        sessionId: '50206d',
        runId: 'run1',
        hypothesisId: 'H1',
        location: 'sut/index.js:openapi-pre',
        message: 'Request reached OpenAPI validator',
        data: { method: req.method, path: req.path },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion agent log
    next();
  });

  app.use(
    OpenApiValidator.middleware({
      apiSpec: path.join(__dirname, 'openapi', 'gateway.yaml'),
      validateRequests: true,
      validateResponses: false,
    })
  );

  // Error-logging middleware to capture OpenAPI NotFound and other errors
  app.use((err, req, res, next) => {
    // #region agent log
    fetch('http://127.0.0.1:7720/ingest/83b26dc7-e0f6-447f-ae08-2bd6e4dc06c6', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Debug-Session-Id': '50206d',
      },
      body: JSON.stringify({
        sessionId: '50206d',
        runId: 'run1',
        hypothesisId: 'H2',
        location: 'sut/index.js:openapi-error',
        message: 'Error after OpenAPI validator',
        data: {
          method: req && req.method,
          path: req && req.path,
          errorMessage: err && err.message,
          errorName: err && err.name,
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {});
    // #endregion agent log
    next(err);
  });

  // ---- REST APIs in scope ----

  app.use('/auth', createAuthRouter({ db, kafka }));

  // GET /products
  app.get('/products', (req, res) => {
    res.json(products);
  });

  // POST /cart/add (requires auth)
  app.post('/cart/add', requireAuth, (req, res) => {
    const userId = Number(req.user && req.user.id) || 1;
    const { productId, quantity } = req.body || {};
    const product = products.find(p => p.id === Number(productId));
    if (!product) {
      return res.status(400).json({ error: 'Invalid productId' });
    }
    if (!quantity || quantity <= 0) {
      return res.status(400).json({ error: 'Invalid quantity' });
    }

    if (!carts[userId]) carts[userId] = [];
    carts[userId].push({ productId: product.id, quantity });

    res.status(201).json({
      message: 'Item added to cart',
      cart: carts[userId]
    });
  });

  // GET /cart/items - return current cart with product details (requires auth)
  app.get('/cart/items', requireAuth, (req, res) => {
    const userId = Number(req.user && req.user.id) || 1;
    const userCart = carts[userId] || [];
    const detailed = userCart.map(item => {
      const product = products.find(p => p.id === item.productId) || {};
      return {
        productId: item.productId,
        name: product.name,
        price: product.price,
        quantity: item.quantity
      };
    });
    res.json(detailed);
  });

  app.get('/order/:orderId', (req, res) => {
    const order = orders[req.params.orderId];
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }
    const detailedItems = order.items.map(item => {
      const product = products.find(p => p.id === item.productId) || {};
      return {
        productId: item.productId,
        name: product.name,
        price: product.price,
        quantity: item.quantity
      };
    });
    res.json({
      id: order.id,
      total: order.total,
      status: order.status,
      items: detailedItems
    });
  });
  // POST /cart/remove - remove one productId from cart (requires auth)
  app.post('/cart/remove', requireAuth, (req, res) => {
    const userId = Number(req.user && req.user.id) || 1;
    const { productId } = req.body || {};
    if (!productId) {
      return res.status(400).json({ error: 'productId is required' });
    }
    const userCart = carts[userId] || [];
    const index = userCart.findIndex(item => item.productId === Number(productId));
    if (index === -1) {
      return res.status(404).json({ error: 'Item not in cart' });
    }
    userCart.splice(index, 1);
    carts[userId] = userCart;
    res.json({ message: 'Item removed', cart: userCart });
  });

  // POST /cart/clear - clear cart for current user (for test isolation, requires auth)
  app.post('/cart/clear', requireAuth, (req, res) => {
    const userId = Number(req.user && req.user.id) || 1;
    carts[userId] = [];
    res.json({ message: 'Cart cleared' });
  });

  // POST /order/create (requires valid user JWT)
  app.post('/order/create', requireAuth, (req, res) => {
    const userId = Number(req.user && req.user.id) || 1;
    const userCart = carts[userId] || [];
    if (userCart.length === 0) {
      return res.status(400).json({ error: 'Cart is empty' });
    }

    const orderId = Date.now().toString();
    const total = userCart.reduce((sum, item) => {
      const product = products.find(p => p.id === item.productId);
      return sum + (product ? product.price * item.quantity : 0);
    }, 0);

    orders[orderId] = {
      id: orderId,
      userId,
      items: userCart,
      total,
      status: 'CREATED'
    };

    // clear cart on order
    carts[userId] = [];

    res.status(201).json({
      message: 'Order created',
      orderId,
      total
    });
  });

  // POST /payment/charge (requires valid user JWT)
  app.post('/payment/charge', requireAuth, (req, res) => {
    const { orderId, cardNumber } = req.body || {};
    const order = orders[orderId];
    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }
    if (!cardNumber || String(cardNumber).length < 4) {
      return res.status(400).json({ error: 'Invalid card details' });
    }

    order.status = 'PAID';

    // Simulate notification via log (placeholder for Kafka/notification service)
    console.log(`Notification: order ${orderId} paid, total=${order.total}`);

    res.json({
      message: 'Payment successful',
      orderId,
      status: order.status
    });
  });

  // Health endpoint for quick checks
  app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
  });

  return app;
}

if (require.main === module) {
  const app = createApp();
  app.listen(PORT, () => {
    console.log(`E-commerce SUT listening on http://localhost:${PORT}`);
  });
}

module.exports = { createApp };
