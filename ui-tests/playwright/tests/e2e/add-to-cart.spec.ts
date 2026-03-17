import { test, expect } from '@playwright/test';
import { ProductsPage } from '../../pages/ProductsPage';
import { CartPage } from '../../pages/CartPage';

test.describe('Add product to cart', () => {
  test.beforeEach(async ({ request }) => {
    await request.post('/cart/clear');
  });
  test('add single product to cart', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);

    await productsPage.searchAndAddFirstProduct('Laptop');

    await cartPage.verifyLoaded();
    await cartPage.addProductToCart();

    const items = await cartPage.cartItems.allTextContents();
    const allText = items.join(' ').toLowerCase();
    expect(allText).toContain('laptop');
  });

  test('add multiple different products to cart', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);

    // Add Laptop
    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();

    // Navigate back to products and add Phone
    await productsPage.productSearch();
    await productsPage.searchAndAddFirstProduct('Phone');

    await cartPage.verifyLoaded();
    const items = await cartPage.cartItems.allTextContents();
    const allText = items.join(' ').toLowerCase();

    expect(allText).toContain('laptop');
    expect(allText).toContain('phone');
  });

  test('add same product twice results in two entries', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);

    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();

    await productsPage.productSearch();
    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();

    const items = await cartPage.cartItems.allTextContents();
    const laptopItems = items.filter(t => t.toLowerCase().includes('laptop'));
    expect(laptopItems.length).toBeGreaterThanOrEqual(2);
  });

  test('remove product from cart after adding', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);

    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();

    await productsPage.productSearch();
    await productsPage.searchAndAddFirstProduct('Phone');
    await cartPage.verifyLoaded();

    const countBefore = await cartPage.cartItems.count();
    await cartPage.removeFirstItem();
    const countAfter = await cartPage.cartItems.count();

    expect(countAfter).toBe(countBefore - 1);
  });

  test('cart persists across navigation', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    const cartPage = new CartPage(page);

    await productsPage.searchAndAddFirstProduct('Laptop');
    await cartPage.verifyLoaded();

    const itemsBefore = await cartPage.cartItems.allTextContents();

    await productsPage.productSearch();
    await cartPage.open();
    await cartPage.verifyLoaded();

    const itemsAfter = await cartPage.cartItems.allTextContents();
    expect(itemsAfter.length).toBe(itemsBefore.length);
  });
});

