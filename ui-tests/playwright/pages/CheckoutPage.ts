import { Page, Locator, expect } from '@playwright/test';

export class CheckoutPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly continueToPaymentLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /checkout/i });
    this.continueToPaymentLink = page.getByRole('link', {
      name: /continue to payment/i,
    });
  }

  async verifyLoaded(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  async goToPayment(): Promise<void> {
    await this.continueToPaymentLink.click();
  }

  // High-level action for "Checkout process" step
  async checkoutProcess(): Promise<void> {
    await this.verifyLoaded();
    await this.goToPayment();
  }
}

