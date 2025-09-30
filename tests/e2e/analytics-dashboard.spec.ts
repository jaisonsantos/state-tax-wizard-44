import { test, expect } from '@playwright/test';

const RUN_ANALYTICS_SMOKE = process.env.ENABLE_ANALYTICS_TEST === '1';

test.describe('analytics dashboard', () => {
  test.skip(!RUN_ANALYTICS_SMOKE, 'Set ENABLE_ANALYTICS_TEST=1 to run analytics dashboard smoke');

  test('renders KPI cards and paginated activity', async ({ page, context }) => {
    const apiBase = process.env.PLAYWRIGHT_API_BASE ?? 'http://localhost:8000/api';
    const appBase = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';

    const loginResponse = await context.request.post(`${apiBase}/auth/login`, {
      data: {
        email: 'analytics@example.com',
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

    await page.goto(`${appBase}/dashboard`);
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

    const cards = page.locator('[data-testid="analytics-card"]');
    await expect(cards.first()).toBeVisible();
    const cardCount = await cards.count();
    expect(cardCount).toBeGreaterThan(0);

    const helperLink = page.getByRole('link', { name: /analytics reference/i });
    await expect(helperLink).toBeVisible();

    const activitySection = page.getByRole('heading', { name: 'Recent Fee Decisions' });
    await expect(activitySection).toBeVisible();

    const loadMoreButton = page.getByRole('button', { name: /Load more activity/ });
    if (await loadMoreButton.isVisible()) {
      await loadMoreButton.click();
      await expect(loadMoreButton).toBeDisabled();
    }

    await page.screenshot({ path: 'dashboard-analytics.png', fullPage: false });
  });
});
