function createDb() {
  return {
    users: [
      {
        id: 1,
        email: 'test@example.com',
        password: 'password123',
      },
    ],
    products: [],
    carts: [],
    orders: [],
    payments: [],
    notifications: [],
  };
}

module.exports = { createDb };

