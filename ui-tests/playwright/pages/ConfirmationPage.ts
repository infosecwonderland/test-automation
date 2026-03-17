import { Page, Locator, expect } from '@playwright/test';

export class ConfirmationPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly orderDetails: Locator;
  readonly orderIdEl: Locator;
  readonly orderTotalEl: Locator;
  readonly orderItems: Locator;
  readonly notificationStatus: Locator;
  readonly noOrderMessage: Locator;
  readonly backToProductsLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', {
      name: /order confirmation/i,
    });
    this.orderDetails = page.getByTestId('order-details');
    this.orderIdEl = page.getByTestId('order-id');
    this.orderTotalEl = page.getByTestId('order-total');
    this.orderItems = page.getByTestId('order-item');
    this.notificationStatus = page.getByTestId('notification-status');
    this.noOrderMessage = page.getByTestId('no-order-message');
    this.backToProductsLink = page.getByTestId('back-to-products');
  }

  async verifyLoaded(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  /** Wait for order details to be populated (async fetch on confirmation page). */
  async waitForOrderDetails(timeoutMs = 10000): Promise<void> {
    await expect(this.orderDetails).toBeVisible({ timeout: timeoutMs });
    await expect(this.orderIdEl).not.toHaveText('', { timeout: timeoutMs });
  }

  async getOrderId(): Promise<string> {
    return (await this.orderIdEl.textContent()) ?? '';
  }

  async getOrderTotal(): Promise<string> {
    return (await this.orderTotalEl.textContent()) ?? '';
  }

  async getOrderItemTexts(): Promise<string[]> {
    const count = await this.orderItems.count();
    const texts: string[] = [];
    for (let i = 0; i < count; i++) {
      texts.push((await this.orderItems.nth(i).textContent()) ?? '');
    }
    return texts;
  }

  async isNoOrderMessageVisible(): Promise<boolean> {
    await this.noOrderMessage.waitFor({ state: 'visible', timeout: 7000 });
    return true;
  }

  async clickBackToProducts(): Promise<void> {
    await this.backToProductsLink.click();
  }

  // High-level action for "Order confirmation" step
  async orderConfirmation(): Promise<void> {
    await this.verifyLoaded();
  }
}
