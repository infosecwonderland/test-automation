const express = require('express');

function createProductRouter({ db }) {
  const router = express.Router();

  router.get('/', (req, res) => {
    res.json(db.products);
  });

  router.post('/', (req, res) => {
    const { name, price, currency } = req.body || {};
    if (!name || typeof price !== 'number' || !currency) {
      return res.status(400).json({ message: 'name, price and currency are required' });
    }

    const product = {
      id: db.products.length + 1,
      name,
      price,
      currency,
    };
    db.products.push(product);
    return res.status(201).json(product);
  });

  router.get('/:id', (req, res) => {
    const id = Number(req.params.id);
    const product = db.products.find((p) => p.id === id);
    if (!product) {
      return res.status(404).json({ message: 'product not found' });
    }
    return res.json(product);
  });

  return router;
}

module.exports = { createProductRouter };

