import { Page, Locator, expect } from '@playwright/test';

export class RegisterPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorMessage: Locator;
  readonly form: Locator;

  constructor(page: Page) {
    this.page = page;
    this.form = page.locator('#register-form');
    this.emailInput = page.locator('#email');
    this.passwordInput = page.locator('#password');
    this.submitButton = page.locator('#submit');
    this.errorMessage = page.locator('#register-error');
  }

  async open(): Promise<void> {
    await this.page.goto('/register');
  }

  async verifyLoaded(): Promise<void> {
    await expect(this.form).toBeVisible();
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
  }

  async register(email: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async registerAndWaitForLogin(email: string, password: string, timeout = 5000): Promise<void> {
    await this.register(email, password);
    await this.page.waitForURL('**/login', { timeout });
  }

  async getErrorMessage(): Promise<string> {
    return (await this.errorMessage.textContent()) ?? '';
  }
}

