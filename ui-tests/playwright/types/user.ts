/**
 * Shared user type for E2E tests. Matches test-data/users.json and SUT auth (email + password).
 */
export type User = {
  email: string;
  password: string;
  role: string;
};
