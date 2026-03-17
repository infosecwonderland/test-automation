import { Page, Locator, expect } from '@playwright/test';

/**
 * Sample ConfirmationPage used by the self-healing layer.
 * healer.py patches selectors here when a broken one is detected.
 */
export class ConfirmationPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly orderDetails: Locator;
  readonly orderIdEl: Locator;
  readonly orderTotalEl: Locator;
  readonly backToProductsLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /order confirmation/i });
    this.orderDetails = page.getByTestId('order-details');
    this.orderIdEl = page.getByTestId('order-id');
    this.orderTotalEl = page.getByTestId('order-total');
    this.backToProductsLink = page.getByTestId('back-to-products');
  }

  async verifyLoaded(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  async waitForOrderDetails(timeoutMs = 10000): Promise<void> {
    await expect(this.orderDetails).toBeVisible({ timeout: timeoutMs });
    await expect(this.orderIdEl).not.toHaveText('', { timeout: timeoutMs });
  }

  async getOrderId(): Promise<string> {
    return (await this.orderIdEl.textContent()) ?? '';
  }

  async clickBackToProducts(): Promise<void> {
    await this.backToProductsLink.click();
  }
}
