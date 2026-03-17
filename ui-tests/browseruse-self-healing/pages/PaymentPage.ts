import { Page, Locator, expect } from '@playwright/test';

/**
 * Sample PaymentPage used by the self-healing layer.
 * healer.py patches selectors here when a broken one is detected.
 */
export class PaymentPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly orderIdInput: Locator;
  readonly cardNumberInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /payment/i });
    this.orderIdInput = page.locator('input[name="orderId"]');
    this.cardNumberInput = page.locator('input[name="cardNumber"]');
    this.submitButton = page.getByRole('button', { name: /pay/i });
    this.errorMessage = page.getByTestId('payment-error');
  }

  async verifyLoaded(): Promise<void> {
    await expect(this.heading).toBeVisible();
  }

  async pay(orderId: string, cardNumber: string): Promise<void> {
    await this.orderIdInput.fill(orderId);
    await this.cardNumberInput.fill(cardNumber);
    await this.submitButton.click();
  }

  async getErrorMessage(): Promise<string> {
    return (await this.errorMessage.textContent()) ?? '';
  }
}
