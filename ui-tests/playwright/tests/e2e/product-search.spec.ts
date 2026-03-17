import { test, expect } from '@playwright/test';
import { ProductsPage } from '../../pages/ProductsPage';

test.describe('Product search', () => {
  test('shows all products when search is empty', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    await productsPage.productSearch();

    const names = await productsPage.getVisibleProductNames();
    // Expect all three demo products to be visible
    expect(names.length).toBe(3);
    expect(names.join(' ')).toContain('Laptop');
    expect(names.join(' ')).toContain('Headphones');
    expect(names.join(' ')).toContain('Phone');
  });

  test('exact-name search returns only matching product', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    await productsPage.search('Laptop');

    const names = await productsPage.getVisibleProductNames();
    expect(names.length).toBeGreaterThan(0);
    // All visible items should contain the searched term
    for (const name of names) {
      expect(name.toLowerCase()).toContain('laptop');
    }
  });

  test('case-insensitive search works', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    await productsPage.search('hEaDpHoNeS');

    const names = await productsPage.getVisibleProductNames();
    expect(names.length).toBeGreaterThan(0);
    for (const name of names) {
      expect(name.toLowerCase()).toContain('headphones');
    }
  });

  test('partial-name search can match multiple products', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    await productsPage.search('phone');

    const names = await productsPage.getVisibleProductNames();
    // Should match \"Phone\" and \"Headphones\"
    expect(names.length).toBeGreaterThanOrEqual(2);
    const allText = names.join(' ').toLowerCase();
    expect(allText).toContain('phone');
    expect(allText).toContain('headphones');
  });

  test('no-match search shows no products', async ({ page }) => {
    const productsPage = new ProductsPage(page);
    await productsPage.search('NonExistingProductXYZ');

    const names = await productsPage.getVisibleProductNames();
    expect(names.length).toBe(0);
  });
});

