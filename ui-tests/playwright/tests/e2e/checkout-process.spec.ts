import { test, expect } from '../../fixtures/allure';
import { ProductsPage } from '../../pages/ProductsPage';
import { CartPage } from '../../pages/CartPage';
import { CheckoutPage } from '../../pages/CheckoutPage';
import { PaymentPage } from '../../pages/PaymentPage';

const TEST_EMAIL = 'test@example.com';
const TEST_PASSWORD = 'password123';

test.describe.configure({ mode: 'serial' });

test.describe('Checkout process', () => {
  test.beforeEach(async ({ page, request }) => {
    // Obtain a JWT token for the pre-seeded test user
    const loginRes = await request.post('/auth/login', {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const { accessToken } = await loginRes.json();

    // Seed the token into localStorage so browser-side getAuthHeaders() works
    await page.goto('/products-page');
    await page.evaluate((token: string) => {
      localStorage.setItem('authToken', token);
    }, accessToken);

    // Start each test with a clean cart for isolation
    await request.post('/cart/clear', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  });

  test('checkout from cart with items navigates to checkout page', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);
    const checkoutPage = new CheckoutPage(page);

    // Add one product to the cart (lands on /cart)
    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();

    // Proceed to checkout
    await cartPage.goToCheckout();

    // Verify checkout page
    await checkoutPage.verifyLoaded();
    await expect(page).toHaveURL(/\/checkout$/);
  });

  test('checkout process continues from checkout to payment page', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);
    const checkoutPage = new CheckoutPage(page);
    const paymentPage = new PaymentPage(page);

    // Ensure we have an item in the cart and navigate to checkout
    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();
    await cartPage.goToCheckout();
    await checkoutPage.verifyLoaded();

    // Run the checkout process step (continue to payment)
    await checkoutPage.checkoutProcess();

    // Verify we reached the payment page
    await paymentPage.verifyLoaded();
    await expect(page).toHaveURL(/\/payment$/);
  });

  test('cannot checkout when cart is empty', async ({ page }) => {
    const cartPage = new CartPage(page);

    // Cart is cleared in beforeEach; open cart directly
    await cartPage.open();
    await cartPage.verifyLoaded();

    // No items should be present
    const count = await cartPage.cartItems.count();
    expect(count).toBe(0);

    // Proceed to checkout button should be disabled
    await expect(cartPage.proceedToCheckoutButton).toBeDisabled();
  });
});

