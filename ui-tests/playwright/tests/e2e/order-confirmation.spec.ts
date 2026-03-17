import { test, expect } from '@playwright/test';
import { ProductsPage } from '../../pages/ProductsPage';
import { CartPage } from '../../pages/CartPage';
import { CheckoutPage } from '../../pages/CheckoutPage';
import { PaymentPage } from '../../pages/PaymentPage';
import { ConfirmationPage } from '../../pages/ConfirmationPage';

test.describe('Order confirmation', () => {
  test.beforeEach(async ({ request }) => {
    await request.post('/cart/clear');
  });

  test('after successful payment, confirmation shows order details and notification', async ({
    page,
  }) => {
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

    await paymentPage.paymentExecution('ignored-order-id', '4111111111111111');

    await page.waitForURL(/\/order-confirmation\?orderId=/, { timeout: 15000 });
    await confirmationPage.orderConfirmation();

    await confirmationPage.waitForOrderDetails(20000);

    const orderId = await confirmationPage.getOrderId();
    expect(orderId.length).toBeGreaterThan(0);

    const total = await confirmationPage.getOrderTotal();
    expect(parseFloat(total)).toBeGreaterThan(0);

    const items = await confirmationPage.getOrderItemTexts();
    expect(items.length).toBeGreaterThan(0);
    expect(items.join(' ').toLowerCase()).toContain('laptop');

    await expect(confirmationPage.notificationStatus).toContainText('Sent');
  });

  test('direct visit to order-confirmation with no order shows no-order message', async ({
    page,
  }) => {
    const confirmationPage = new ConfirmationPage(page);

    await page.goto('/order-confirmation');
    await confirmationPage.verifyLoaded();

    const visible = await confirmationPage.isNoOrderMessageVisible();
    expect(visible).toBe(true);
  });

  test('direct visit with invalid orderId shows no-order message', async ({ page }) => {
    const confirmationPage = new ConfirmationPage(page);

    await page.goto('/order-confirmation?orderId=invalid-id-999');
    await confirmationPage.verifyLoaded();

    const visible = await confirmationPage.isNoOrderMessageVisible();
    expect(visible).toBe(true);
  });

  test('back to products link navigates to products page', async ({ page }) => {
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

    await paymentPage.paymentExecution('ignored-order-id', '4111111111111111');
    await confirmationPage.orderConfirmation();

    await confirmationPage.clickBackToProducts();

    await expect(page).toHaveURL(/\/products-page/);
    await productsPage.verifyLoaded();
  });
});
