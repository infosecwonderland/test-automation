import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly loginButton: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly containerSection: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.loginButton = page.locator('#login');
    this.emailInput = page.locator('#email');
    this.passwordInput = page.locator('#password');
    this.submitButton = page.locator('#submit');
    this.containerSection = page.locator('#login-form');
    this.errorMessage = page.getByTestId('login-error');
  }

  async open(): Promise<void> {
    await this.page.goto('/');
  }

  async clickLogin(): Promise<void> {
    await this.loginButton.click();
  }

  async enterEmail(email: string): Promise<void> {
    await this.emailInput.fill(email);
  }

  async enterPassword(password: string): Promise<void> {
    await this.passwordInput.fill(password);
  }

  async clickSubmit(): Promise<void> {
    await this.submitButton.click();
  }

  async login(email: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async loginWithWait(
    email: string,
    password: string,
    timeout: number = 5000
  ): Promise<void> {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
    await this.containerSection.waitFor({ state: 'detached', timeout });
  }

  async getErrorMessage(): Promise<string> {
    return (await this.errorMessage.textContent()) ?? '';
  }

  // High-level action for "User login" in the plan
  async userLogin(email: string, password: string): Promise<void> {
    await this.open();
    await this.verifyLoginFormVisible();
    await this.login(email, password);
  }

  async userLoginWithWait(
    email: string,
    password: string,
    timeout?: number
  ): Promise<void> {
    await this.open();
    await this.verifyLoginFormVisible();
    await this.loginWithWait(email, password, timeout ?? 5000);
  }

  async verifyLoginFormVisible(): Promise<void> {
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
  }
}