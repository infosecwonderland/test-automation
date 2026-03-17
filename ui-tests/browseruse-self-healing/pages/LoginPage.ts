import { Page, Locator, expect } from '@playwright/test';

/**
 * Sample LoginPage used by the self-healing layer.
 * healer.py patches the selectors here when a broken one is detected.
 * The canonical page object lives in ../playwright/pages/LoginPage.ts.
 */
export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.locator('#email');
    this.passwordInput = page.locator('#password');
    this.submitButton = page.locator('#submit');
    this.errorMessage = page.getByTestId('login-error');
  }

  async open(): Promise<void> {
    await this.page.goto('/');
  }

  async login(email: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async verifyLoginFormVisible(): Promise<void> {
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
  }

  async getErrorMessage(): Promise<string> {
    return (await this.errorMessage.textContent()) ?? '';
  }
}
