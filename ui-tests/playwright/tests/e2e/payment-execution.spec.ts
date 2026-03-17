import { test, expect } from '@playwright/test';
import { ProductsPage } from '../../pages/ProductsPage';
import { CartPage } from '../../pages/CartPage';
import { CheckoutPage } from '../../pages/CheckoutPage';
import { PaymentPage } from '../../pages/PaymentPage';
import { ConfirmationPage } from '../../pages/ConfirmationPage';

test.describe('Payment execution', () => {
  test.beforeEach(async ({ request }) => {
    await request.post('/cart/clear');
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

    const msg = await paymentPage.getErrorMessage();
    expect(msg).toContain('Unable to create order');
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

    const msg = await paymentPage.getErrorMessage();
    expect(msg).toContain('Payment failed');
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

    const msg = await paymentPage.getErrorMessage();
    expect(msg).toContain('Payment failed');
    await expect(page).toHaveURL(/\/payment$/);
  });
});

