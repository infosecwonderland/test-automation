import { test } from '@playwright/test';
import { LoginPage } from '../../pages/LoginPage';
import { ProductsPage } from '../../pages/ProductsPage';
import { CartPage } from '../../pages/CartPage';
import { CheckoutPage } from '../../pages/CheckoutPage';
import { PaymentPage } from '../../pages/PaymentPage';
import { ConfirmationPage } from '../../pages/ConfirmationPage';
import { loadJson } from '../../utils/testDataLoader';
import { attachNetworkLogger } from '../../utils/networkLogger';
import type { User } from '../../types/user';

test.describe('E-commerce purchase flow', () => {
  test('user can complete purchase UI flow', async ({ page }) => {
    // Load test user data from external JSON to avoid hardcoding secrets
    const users = loadJson<User[]>('test-data/users.json');
    const user = users[0];

    await attachNetworkLogger(page, 'E2E purchase flow');

    const loginPage = new LoginPage(page);
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);
    const checkoutPage = new CheckoutPage(page);
    const paymentPage = new PaymentPage(page);
    const confirmationPage = new ConfirmationPage(page);

    // User login (wait for redirect to product search)
    await loginPage.userLoginWithWait(user.email, user.password);

    // Product search + add product to cart
    await productsPage.searchAndAddFirstProduct('Laptop');

    // Add product to cart (view cart)
    await cartPage.addProductToCart();
    await cartPage.goToCheckout();

    // Checkout process
    await checkoutPage.checkoutProcess();

    // Payment execution (UI now creates order + charges it, then redirects)
    await paymentPage.paymentExecution('ignored-order-id', '4111111111111111');

    // Order confirmation
    await confirmationPage.orderConfirmation();
  });
});