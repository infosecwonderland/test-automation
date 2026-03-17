import { Page, Locator, expect } from '@playwright/test';

/**
 * Sample ProductsPage used by the self-healing layer.
 * healer.py patches selectors here when a broken one is detected.
 */
export class ProductsPage {
  readonly page: Page;
  readonly searchInput: Locator;
  readonly productItems: Locator;
  readonly addToCartButtons: Locator;

  constructor(page: Page) {
    this.page = page;
    this.searchInput = page.locator('#search');
    this.productItems = page.getByTestId('product-item');
    this.addToCartButtons = page.getByTestId('add-to-cart-button');
  }

  async open(): Promise<void> {
    await this.page.goto('/products-page');
  }

  async search(text: string): Promise<void> {
    await this.searchInput.fill(text);
  }

  async addFirstProductToCart(): Promise<void> {
    await expect(this.productItems.first()).toBeVisible();
    await this.addToCartButtons.first().click();
  }
}
