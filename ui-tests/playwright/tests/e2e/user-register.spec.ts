import { test, expect } from '@playwright/test';
import { RegisterPage } from '../../pages/RegisterPage';
import { LoginPage } from '../../pages/LoginPage';

test.describe('User registration (E2E)', () => {
  test('new user can register and then log in', async ({ page }) => {
    const registerPage = new RegisterPage(page);
    const loginPage = new LoginPage(page);

    const uniqueEmail = `user+${Date.now()}@example.com`;
    const password = 'password123';

    await registerPage.open();
    await registerPage.verifyLoaded();

    await registerPage.registerAndWaitForLogin(uniqueEmail, password, 5000);

    await loginPage.verifyLoginFormVisible();
    await loginPage.loginWithWait(uniqueEmail, password, 5000);

    await page.waitForURL('**/products-page');
  });

  test('registering an existing email shows error', async ({ page }) => {
    const registerPage = new RegisterPage(page);

    // Seed user exists in SUT db: test@example.com / password123
    await registerPage.open();
    await registerPage.verifyLoaded();

    await registerPage.register('test@example.com', 'password123');

    await registerPage.errorMessage.waitFor({ state: 'visible', timeout: 5000 });
    const msg = await registerPage.getErrorMessage();
    expect(msg.toLowerCase()).toContain('user already exists');
  });
});

