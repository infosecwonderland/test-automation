import { test, expect } from '@playwright/test';
import { ProductsPage } from '../../pages/ProductsPage';
import { CartPage } from '../../pages/CartPage';
import { CheckoutPage } from '../../pages/CheckoutPage';
import { PaymentPage } from '../../pages/PaymentPage';
import { ConfirmationPage } from '../../pages/ConfirmationPage';

const TEST_EMAIL = 'test@example.com';
const TEST_PASSWORD = 'password123';

test.describe.configure({ mode: 'serial' });

test.describe('Payment execution', () => {
  test.beforeEach(async ({ page, request }) => {
    const loginRes = await request.post('/auth/login', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const { accessToken } = await loginRes.json();

    await page.goto('/products-page');
    await page.evaluate((token: string) => {
      localStorage.setItem('authToken', token);
    }, accessToken);

    await request.post('/cart/clear', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  });

  test('payment form is visible when reached from checkout', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);
    const checkoutPage = new CheckoutPage(page);
    const paymentPage = new PaymentPage(page);

    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();
    await cartPage.goToCheckout();
    await checkoutPage.verifyLoaded();

    await checkoutPage.checkoutProcess();
    await paymentPage.verifyLoaded();

    await expect(paymentPage.cardNumberInput).toBeVisible();
    await expect(paymentPage.submitButton).toBeVisible();
  });

  test('successful payment redirects to order confirmation', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);
    const checkoutPage = new CheckoutPage(page);
    const paymentPage = new PaymentPage(page);
    const confirmationPage = new ConfirmationPage(page);

    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();
    await cartPage.goToCheckout();
    await checkoutPage.verifyLoaded();

    await checkoutPage.checkoutProcess();

    // UI flow creates order and charges payment
    await paymentPage.paymentExecution('ignored-order-id', '4111111111111111');

    await confirmationPage.orderConfirmation();
    await expect(page).toHaveURL(/\/order-confirmation\?orderId=/);
  });

  test('cannot execute payment when cart is empty', async ({ page }) => {
    const paymentPage = new PaymentPage(page);

    // Go directly to payment page with empty cart
    await page.goto('/payment');
    await paymentPage.verifyLoaded();

    await paymentPage.paymentExecution('ignored-order-id', '4111111111111111');

    await expect(paymentPage.errorMessage).toContainText('Unable to create order');
    await expect(page).toHaveURL(/\/payment$/);
  });

  test('blank card number shows error', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);
    const checkoutPage = new CheckoutPage(page);
    const paymentPage = new PaymentPage(page);

    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();
    await cartPage.goToCheckout();
    await checkoutPage.verifyLoaded();

    await checkoutPage.checkoutProcess();
    await paymentPage.verifyLoaded();

    // Blank card number
    await paymentPage.paymentExecution('ignored-order-id', '');

    await expect(paymentPage.errorMessage).toContainText('Payment failed');
    await expect(page).toHaveURL(/\/payment$/);
  });

  test('invalid short card number shows error', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);
    const checkoutPage = new CheckoutPage(page);
    const paymentPage = new PaymentPage(page);

    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();
    await cartPage.goToCheckout();
    await checkoutPage.verifyLoaded();

    await checkoutPage.checkoutProcess();
    await paymentPage.verifyLoaded();

    // Too short card number
    await paymentPage.paymentExecution('ignored-order-id', '123');

    await expect(paymentPage.errorMessage).toContainText('Payment failed');
    await expect(page).toHaveURL(/\/payment$/);
  });
});

