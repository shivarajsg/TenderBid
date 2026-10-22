import { test, expect } from '@playwright/test';

test.describe('Phase 11 Live Ingestion Acceptance Test — Real New Tender in React Catalogue', () => {

  test('Newly ingested tender appears in React catalogue with portal badge, link and metadata', async ({ page }) => {
    // Generate valid auth token matching live.msme@tenderplatform.com in DB
    // Token payload subject: b4c19058-8470-4219-a5fc-7e3b3d3d3f60
    const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiNGMxOTA1OC04NDcwLTQyMTktYTVmYy03ZTNiM2QzZDNmNjAiLCJyb2xlIjoiTVNNRV9VU0VSIiwiY29tcGFueV9pZCI6bnVsbCwiaWF0IjoxNzkyNTk3MTU4LCJleHAiOjE3OTMyMDE5NTgsInR5cGUiOiJhY2Nlc3MifQ.iX-58RCqogf0ppd53aaGBW-QBgahgtt_gNHiwfUh1ZA";

    // Set token in sessionStorage before navigating
    await page.addInitScript((tok) => {
      sessionStorage.setItem('tender_bid_token', tok);
    }, token);

    // We can intercept auth/me or let it pass through to the real backend if token is valid
    // For reliable browser testing, let's mock auth/me to live.msme and let all tenders APIs hit the real backend
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'b4c19058-8470-4219-a5fc-7e3b3d3d3f60',
            email: 'live.msme@tenderplatform.com',
            full_name: 'Live MSME Test User',
            role: 'MSME_USER',
            is_active: true,
            created_at: '2026-10-21T00:00:00Z',
          },
        }),
      });
    });

    await page.route('**/api/v1/notifications/unread-count', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ unread_count: 0 }),
      });
    });

    // Notice we do NOT mock /api/v1/tenders* — it routes to the real FastAPI backend on port 8000!

    // 1. Visit tender catalogue
    await page.goto('/tenders');
    await page.waitForLoadState('networkidle');

    // 2. Verify page heading
    await expect(page.getByRole('heading', { name: 'Tender Opportunities' })).toBeVisible();

    // 3. Verify newly ingested tender GEM-2026-B-999888 is displayed in catalogue
    const newTenderCard = page.locator('text=Automated Supply of Edge AI Telemetry Computing Units for Smart Grid Substations').first();
    await expect(newTenderCard).toBeVisible({ timeout: 5000 });

    // 4. Verify its source label and portal badge
    const gemBadge = page.locator('text=GeM Portal').first();
    await expect(gemBadge).toBeVisible();

    // 5. Verify the official portal link is present and correct
    const portalLink = page.locator('a[href="https://bidplus.gem.gov.in/showbidDocument/GEM-2026-B-999888"]');
    await expect(portalLink).toBeVisible();
    await expect(portalLink).toHaveAttribute('target', '_blank');

    // 6. Test Catalogue Refresh
    const refreshButton = page.getByRole('button', { name: 'Refresh Feed' });
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForLoadState('networkidle');
      await expect(newTenderCard).toBeVisible();
    }

    // 7. Filter by GeM portal
    const gemFilterPill = page.locator('button:has-text("GeM Portal")').first();
    await gemFilterPill.click();
    await page.waitForLoadState('networkidle');

    // Newly imported GeM tender is still visible
    await expect(newTenderCard).toBeVisible();

    console.log('[Acceptance Verification] Successfully verified newly ingested tender on React tender catalogue page.');
  });
});
