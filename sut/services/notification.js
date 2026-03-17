const express = require('express');

function createNotificationRouter({ db, kafka }) {
  const router = express.Router();

  kafka.subscribe('user.registered', (event) => {
    db.notifications.push({
      id: db.notifications.length + 1,
      type: 'WELCOME_EMAIL',
      userId: event.userId,
      payload: { email: event.email },
    });
  });

  kafka.subscribe('order.created', (event) => {
    db.notifications.push({
      id: db.notifications.length + 1,
      type: 'ORDER_CREATED',
      userId: event.userId,
      payload: { orderId: event.orderId, totalAmount: event.totalAmount, currency: event.currency },
    });
  });

  kafka.subscribe('payment.confirmed', (event) => {
    db.notifications.push({
      id: db.notifications.length + 1,
      type: 'PAYMENT_CONFIRMATION',
      userId: null,
      payload: { paymentId: event.paymentId, orderId: event.orderId, amount: event.amount, currency: event.currency },
    });
  });

  router.get('/', (req, res) => {
    res.json(db.notifications);
  });

  router.get('/:id', (req, res) => {
    const id = Number(req.params.id);
    const notification = db.notifications.find((n) => n.id === id);
    if (!notification) {
      return res.status(404).json({ message: 'notification not found' });
    }
    return res.json(notification);
  });

  return router;
}

module.exports = { createNotificationRouter };

