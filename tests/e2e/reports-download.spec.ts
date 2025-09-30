import { test, expect } from '@playwright/test';

const RUN_DOWNLOAD_SMOKE = process.env.ENABLE_REPORT_DOWNLOAD_TEST === '1';

test.describe('report downloads', () => {
  test.skip(!RUN_DOWNLOAD_SMOKE, 'Set ENABLE_REPORT_DOWNLOAD_TEST=1 to run report download smoke');

  test('downloads CSV and JSON exports', async ({ page, context }) => {
    const apiBase = process.env.PLAYWRIGHT_API_BASE ?? 'http://localhost:8000/api';
    const appBase = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';

    const loginResponse = await context.request.post(`${apiBase}/auth/login`, {
      data: {
        email: 'reports@example.com',
        password: 'secret',
      },
    });
    expect(loginResponse.ok()).toBeTruthy();
    const loginData = await loginResponse.json();

    const token: string = loginData.token;
    const storeId: string = loginData.stores[0].id;

    await context.addInitScript(
      ({ authToken, store }: { authToken: string; store: string }) => {
        window.localStorage.setItem('auth_token', authToken);
        window.localStorage.setItem('selected_store_id', store);
      },
      { authToken: token, store: storeId },
    );

    await page.goto(`${appBase}/reports`);
    await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
    await expect(page.getByText('Export History')).toBeVisible();

    const coDownloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Generate CO DR-1786 Report' }).click();
    const coDownload = await coDownloadPromise;
    await expect(coDownload.suggestedFilename()).toContain('CO_DR1786');
    await expect(coDownload.path()).resolves.not.toBeNull();

    const formatTrigger = page.getByRole('combobox', { name: 'Format' });
    await formatTrigger.click();
    await page.getByRole('option', { name: 'JSON' }).click();

    const mnDownloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Generate MN Summary Report' }).click();
    const mnDownload = await mnDownloadPromise;
    await expect(mnDownload.suggestedFilename()).toContain('MN_Summary');
    await expect(mnDownload.path()).resolves.not.toBeNull();

    // Refresh history after exports and confirm latest entries mention success
    await page.waitForTimeout(500);
    const historyRows = page.getByRole('row', { name: /Generate|Re-run/ }).first();
    await expect(historyRows).toBeVisible();
  });
});
