import { Page, Locator, expect } from '@playwright/test';

export class ProductsPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly goToCartLink: Locator;
  readonly searchInput: Locator;
  readonly productItems: Locator;
  readonly addToCartButtons: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /products/i });
    // goToCartLink is currently unused; navigation to cart happens
    // via the "Add to cart" button redirect.
    this.goToCartLink = page.getByRole('link', { name: /go to cart/i }).first().or(page.locator('a[href="/cart"]'));
    this.searchInput = page.locator('#search');
    this.productItems = page.getByTestId('product-item');
    this.addToCartButtons = page.getByTestId('add-to-cart-button');
  }

  async open(): Promise<void> {
    await this.page.goto('/products-page');
  }

  async verifyLoaded(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  async goToCart(): Promise<void> {
    await this.goToCartLink.click();
  }

  // High-level action for "Product search" step
  async productSearch(): Promise<void> {
    await this.open();
    await this.verifyLoaded();
  }

  async search(text: string): Promise<void> {
    await this.productSearch();
    await this.searchInput.fill(text);
  }

  async getVisibleProductNames(): Promise<string[]> {
    const count = await this.productItems.count();
    const names: string[] = [];
    for (let i = 0; i < count; i += 1) {
      const text = (await this.productItems.nth(i).textContent()) ?? '';
      names.push(text);
    }
    return names;
  }

  // Product search + select first matching product and add to cart
  async searchAndAddFirstProduct(searchText: string): Promise<void> {
    await this.productSearch();
    await this.searchInput.fill(searchText);
    await expect(this.productItems.first()).toBeVisible();
    await this.addToCartButtons.first().click();
  }
}

