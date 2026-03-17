import { Page, Locator, expect } from '@playwright/test';

export class CartPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly proceedToCheckoutButton: Locator;
  readonly cartItems: Locator;
  readonly removeButtons: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /cart/i });
    this.proceedToCheckoutButton = page.getByRole('button', {
      name: /proceed to checkout/i,
    });
    this.cartItems = page.getByTestId('cart-item');
    this.removeButtons = page.getByTestId('remove-from-cart-button');
  }

  async open(): Promise<void> {
    await this.page.goto('/cart');
  }

  async verifyLoaded(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  async goToCheckout(): Promise<void> {
    await this.proceedToCheckoutButton.click();
  }

  // High-level action for "Add product to cart" + view cart.
  async addProductToCart(): Promise<void> {
    await this.verifyLoaded();
    await expect(this.cartItems.first()).toBeVisible();
  }

  // Remove first item from the cart
  async removeFirstItem(): Promise<void> {
    const countBefore = await this.cartItems.count();
    if (countBefore === 0) return;
    await this.removeButtons.first().click();
    await expect(this.cartItems).toHaveCount(countBefore - 1);
  }
}

