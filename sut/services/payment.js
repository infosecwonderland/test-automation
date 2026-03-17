const express = require('express');

function createPaymentRouter({ db, kafka }) {
  const router = express.Router();

  router.get('/', (req, res) => {
    res.json(db.payments);
  });

  router.post('/', (req, res) => {
    const { orderId, amount, currency, method } = req.body || {};
    if (!orderId || typeof amount !== 'number' || !currency || !method) {
      return res.status(400).json({ message: 'orderId, amount, currency and method are required' });
    }

    const order = db.orders.find((o) => o.id === orderId);
    if (!order) {
      return res.status(404).json({ message: 'order not found' });
    }

    const payment = {
      id: db.payments.length + 1,
      orderId,
      amount,
      currency,
      method,
      status: 'CONFIRMED',
    };
    db.payments.push(payment);

    order.status = 'PAID';

    kafka.publish('payment.confirmed', { paymentId: payment.id, orderId: order.id, amount, currency });

    return res.status(201).json(payment);
  });

  router.post('/charge', (req, res) => {
    const { orderId, cardNumber } = req.body || {};
    if (!orderId || !cardNumber) {
      return res.status(400).json({ message: 'orderId and cardNumber are required' });
    }

    const order = db.orders.find((o) => o.id === orderId);
    if (!order) {
      return res.status(404).json({ message: 'order not found' });
    }

    if (String(cardNumber).length < 4) {
      return res.status(400).json({ message: 'Invalid card details' });
    }

    order.status = 'PAID';

    const payment = {
      id: db.payments.length + 1,
      orderId: order.id,
      amount: order.totalAmount,
      currency: 'USD',
      method: 'CARD',
      status: 'CONFIRMED',
    };

    db.payments.push(payment);

    kafka.publish('payment.charged', { paymentId: payment.id, orderId: order.id, amount: payment.amount, currency: payment.currency });

    return res.json({ message: 'Payment successful', orderId: order.id, status: order.status });
  });

  return router;
}

module.exports = { createPaymentRouter };

