const express = require('express');
const jwt = require('jsonwebtoken');

// In-memory rate limiting for login attempts (per IP + email).
// This is separate from the generic per-path limiter in index.js so that
// aggressive failed logins are throttled but a later valid login can still
// succeed for other tests.
const LOGIN_WINDOW_MS = 10000; // 10 seconds
const LOGIN_MAX_ATTEMPTS = 5;  // allow first 5 failed attempts, then throttle
const loginBuckets = new Map();

function getLoginBucketKey(ip, email) {
  return `${ip}:${email}`;
}

function recordFailedLogin(ip, email) {
  const key = getLoginBucketKey(ip, email);
  const now = Date.now();
  const bucket =
    loginBuckets.get(key) || { count: 0, resetAt: now + LOGIN_WINDOW_MS };

  if (now > bucket.resetAt) {
    bucket.count = 0;
    bucket.resetAt = now + LOGIN_WINDOW_MS;
  }

  bucket.count += 1;
  loginBuckets.set(key, bucket);
  return bucket;
}

function canAttemptLogin(ip, email) {
  const key = getLoginBucketKey(ip, email);
  const now = Date.now();
  const bucket = loginBuckets.get(key);
  if (!bucket) return true;
  if (now > bucket.resetAt) return true;
  return bucket.count < LOGIN_MAX_ATTEMPTS;
}

function resetLoginBucket(ip, email) {
  const key = getLoginBucketKey(ip, email);
  loginBuckets.delete(key);
}

function createAuthRouter({ db, kafka, jwtSecret }) {
  const JWT_SECRET = jwtSecret;
  const router = express.Router();

  router.post('/register', (req, res) => {
    const { email, password } = req.body || {};
    if (!email || !password) {
      return res.status(400).json({ message: 'email and password are required' });
    }

    const existing = db.users.find((u) => u.email === email);
    if (existing) {
      return res.status(409).json({ message: 'user already exists' });
    }

    const user = {
      id: db.users.length + 1,
      email,
      password,
    };
    db.users.push(user);

    kafka.publish('user.registered', { userId: user.id, email: user.email });

    return res.status(201).json({ id: user.id, email: user.email });
  });

  router.post('/login', (req, res) => {
    const { email, password } = req.body || {};
    if (!email || !password) {
      return res.status(400).json({ message: 'email and password are required' });
    }

    const ip = req.ip || (req.connection && req.connection.remoteAddress) || 'unknown';

    // Check login-specific rate limiting based on recent failed attempts.
    if (!canAttemptLogin(ip, email)) {
      return res.status(429).json({ error: 'Too Many Requests' });
    }

    const user = db.users.find((u) => u.email === email && u.password === password);
    if (!user) {
      const bucket = recordFailedLogin(ip, email);
      if (bucket.count > LOGIN_MAX_ATTEMPTS) {
        return res.status(429).json({ error: 'Too Many Requests' });
      }
      return res.status(401).json({ message: 'invalid credentials' });
    }

    // Successful login should reset failures for this ip/email.
    resetLoginBucket(ip, email);

    const token = jwt.sign(
      { sub: String(user.id), email: user.email },
      JWT_SECRET,
      { expiresIn: '1h' }
    );
    return res.json({ accessToken: token, tokenType: 'Bearer' });
  });

  router.get('/me', (req, res) => {
    const authHeader = req.headers.authorization || '';
    const [, token] = authHeader.split(' ');
    if (!token) {
      return res.status(401).json({ message: 'missing token' });
    }

    try {
      const payload = jwt.verify(token, JWT_SECRET);
      const userId = Number(payload.sub);
      const user = db.users.find((u) => u.id === userId);
      if (!user) {
        return res.status(404).json({ message: 'user not found' });
      }
      return res.json({ id: user.id, email: user.email });
    } catch (err) {
      return res.status(401).json({ message: 'invalid token' });
    }
  });

  return router;
}

module.exports = { createAuthRouter };

