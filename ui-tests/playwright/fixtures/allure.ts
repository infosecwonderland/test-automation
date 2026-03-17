import { test as base } from '@playwright/test';
import { allure } from 'allure-playwright';

export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    allure.parentSuite('UI Tests');
    allure.suite('Playwright');
    allure.subSuite(testInfo.titlePath[0] ?? '');
    await use(page);
  },
});

export { expect } from '@playwright/test';
