import { Page, Locator, expect } from '@playwright/test';

/**
 * Sample CartPage used by the self-healing layer.
 * healer.py patches selectors here when a broken one is detected.
 */
export class CartPage {
  readonly page: Page;
  readonly cartItems: Locator;
  readonly removeButtons: Locator;
  readonly proceedToCheckoutButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.cartItems = page.getByTestId('cart-item');
    this.removeButtons = page.getByTestId('remove-from-cart-button');
    this.proceedToCheckoutButton = page.getByRole('button', {
      name: /proceed to checkout/i,
    });
  }

  async open(): Promise<void> {
    await this.page.goto('/cart');
  }

  async goToCheckout(): Promise<void> {
    await this.proceedToCheckoutButton.click();
  }
}
