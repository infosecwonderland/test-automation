import type { Page, APIResponse } from '@playwright/test';

const NETWORK_DEBUG_ENABLED = process.env.NETWORK_DEBUG === '1';

type NetworkEntry = {
  method: string;
  url: string;
  status?: number;
};

const DEBUG_PATHS = ['/auth/', '/products', '/cart/', '/order/', '/payment/'];

export async function attachNetworkLogger(page: Page, testName: string): Promise<void> {
  if (!NETWORK_DEBUG_ENABLED) {
    return;
  }

  const entries: NetworkEntry[] = [];

  page.on('request', (req) => {
    const url = req.url();
    if (!DEBUG_PATHS.some((p) => url.includes(p))) return;
    entries.push({ method: req.method(), url });
  });

  page.on('response', (res: APIResponse) => {
    const url = res.url();
    if (!DEBUG_PATHS.some((p) => url.includes(p))) return;
    entries.push({ method: res.request().method(), url, status: res.status() });
  });

  page.on('close', () => {
    if (!entries.length) return;
    // eslint-disable-next-line no-console
    console.log(`\n[NETWORK DEBUG] ${testName}`);
    for (const e of entries) {
      // eslint-disable-next-line no-console
      console.log(`  ${e.method} ${e.status ?? ''} ${e.url}`);
    }
  });
}

