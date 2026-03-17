const express = require('express');

function createOrderRouter({ db, kafka }) {
  const router = express.Router();

  router.get('/', (req, res) => {
    res.json(db.orders);
  });

  router.post('/', (req, res) => {
    const { userId, items, totalAmount, currency } = req.body || {};
    if (!userId || !Array.isArray(items) || typeof totalAmount !== 'number' || !currency) {
      return res.status(400).json({ message: 'userId, items, totalAmount and currency are required' });
    }

    const order = {
      id: db.orders.length + 1,
      userId,
      items,
      totalAmount,
      currency,
      status: 'PENDING_PAYMENT',
    };
    db.orders.push(order);

    kafka.publish('order.created', { orderId: order.id, userId: order.userId, totalAmount: order.totalAmount, currency });

    return res.status(201).json(order);
  });

  router.get('/:id', (req, res) => {
    const id = Number(req.params.id);
    const order = db.orders.find((o) => o.id === id);
    if (!order) {
      return res.status(404).json({ message: 'order not found' });
    }
    return res.json(order);
  });

  router.post('/from-cart', (req, res) => {
    const { userId } = req.body || {};
    if (!userId) {
      return res.status(400).json({ message: 'userId is required to create order from cart' });
    }

    const cart = db.carts.find((c) => c.userId === userId);
    if (!cart || !Array.isArray(cart.items) || cart.items.length === 0) {
      return res.status(400).json({ message: 'Cart is empty' });
    }

    const totalAmount = cart.items.reduce((sum, item) => {
      const product = db.products.find((p) => p.id === item.productId);
      return sum + (product ? product.price * item.quantity : 0);
    }, 0);

    const order = {
      id: db.orders.length + 1,
      userId,
      items: cart.items,
      totalAmount,
      currency: 'USD',
      status: 'PENDING_PAYMENT',
    };

    db.orders.push(order);
    cart.items = [];

    kafka.publish('order.created', { orderId: order.id, userId: order.userId, totalAmount: order.totalAmount, currency: order.currency });

    return res.status(201).json(order);
  });

  return router;
}

module.exports = { createOrderRouter };

