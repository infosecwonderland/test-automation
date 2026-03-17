const express = require('express');

function createCartRouter({ db }) {
  const router = express.Router();

  router.get('/:userId', (req, res) => {
    const userId = Number(req.params.userId);
    let cart = db.carts.find((c) => c.userId === userId);
    if (!cart) {
      cart = { userId, items: [] };
      db.carts.push(cart);
    }
    res.json(cart);
  });

  router.post('/:userId/items', (req, res) => {
    const userId = Number(req.params.userId);
    const { productId, quantity } = req.body || {};
    if (!productId || typeof quantity !== 'number') {
      return res.status(400).json({ message: 'productId and quantity are required' });
    }

    let cart = db.carts.find((c) => c.userId === userId);
    if (!cart) {
      cart = { userId, items: [] };
      db.carts.push(cart);
    }

    const existingItem = cart.items.find((i) => i.productId === productId);
    if (existingItem) {
      existingItem.quantity += quantity;
    } else {
      cart.items.push({ productId, quantity });
    }

    return res.status(201).json(cart);
  });

  router.delete('/:userId/items/:productId', (req, res) => {
    const userId = Number(req.params.userId);
    const productId = Number(req.params.productId);

    const cart = db.carts.find((c) => c.userId === userId);
    if (!cart) {
      return res.status(404).json({ message: 'cart not found' });
    }

    cart.items = cart.items.filter((i) => i.productId !== productId);
    return res.status(204).send();
  });

  router.get('/:userId/items/list', (req, res) => {
    const userId = Number(req.params.userId);
    let cart = db.carts.find((c) => c.userId === userId);
    if (!cart) {
      cart = { userId, items: [] };
      db.carts.push(cart);
    }
    return res.json(cart.items);
  });

  router.delete('/:userId/items/clear', (req, res) => {
    const userId = Number(req.params.userId);
    const cart = db.carts.find((c) => c.userId === userId);
    if (!cart) {
      return res.status(204).send();
    }
    cart.items = [];
    return res.status(204).send();
  });

  return router;
}

module.exports = { createCartRouter };

