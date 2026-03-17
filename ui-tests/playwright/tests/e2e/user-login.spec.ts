import { test, expect } from '../../fixtures/allure';
import { LoginPage } from '../../pages/LoginPage';
import { loadJson } from '../../utils/testDataLoader';
import type { User } from '../../types/user';

test.describe('User login (E2E)', () => {
  test('successful login redirects to product search page', async ({ page }) => {
    const users = loadJson<User[]>('test-data/users.json');
    const user = users[0];

    const loginPage = new LoginPage(page);

    await loginPage.open();
    await loginPage.verifyLoginFormVisible();

    // Login and wait for form to disappear (redirect to products-page)
    await loginPage.loginWithWait(user.email, user.password, 5000);

    await page.waitForURL('**/products-page');
  });

  test('invalid credentials show error message', async ({ page }) => {
    const loginPage = new LoginPage(page);

    await loginPage.open();
    await loginPage.verifyLoginFormVisible();

    await loginPage.login('wronguser@example.com', 'wrongpass');

    await page.getByTestId('login-error').waitFor({ state: 'visible', timeout: 5000 });
    const message = await loginPage.getErrorMessage();
    expect(message.toLowerCase()).toContain('invalid credentials');
  });
});
