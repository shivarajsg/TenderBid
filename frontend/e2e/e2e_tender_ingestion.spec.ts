import { test, expect } from '@playwright/test';

test.describe('Phase 11: Government Tender Ingestion End-to-End User Journeys', () => {

  test('Journey 1: MSME Tender Catalogue Displays Automated Government Ingested Tenders & Source Badges', async ({ page }) => {
    // 1. Set Session Storage Token before load
    await page.addInitScript(() => {
      sessionStorage.setItem('tender_bid_token', 'msme-token-11');
    });

    // 2. Mock Authentication & Company
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'u-msme-01',
            email: 'msme@example.com',
            full_name: 'Rajesh Sharma',
            role: 'MSME_USER',
            is_active: true,
            created_at: '2026-10-01T00:00:00Z',
          },
        }),
      });
    });

    await page.route('**/api/v1/company/profile', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'c-01',
            owner_id: 'u-msme-01',
            legal_name: 'Sharma Electricals Pvt Ltd',
            sector: 'Electrical Infrastructure',
            created_at: '2026-10-01T00:00:00Z',
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

    // 3. Mock /api/v1/tenders returning automated government ingested tenders
    await page.route('**/api/v1/tenders*', async (route) => {
      const url = route.request().url();
      if (url.includes('/ingestion/status')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            scheduler_running: true,
            scheduler_interval_seconds: 3600,
            portals: [
              {
                portal_name: 'GEM',
                portal_title: 'Government e-Marketplace (GeM)',
                status: 'ACTIVE',
                official_url: 'https://gem.gov.in',
                access_mode: 'Verified High-Fidelity GeM Procurement Feed',
                total_tenders_ingested: 4,
              },
              {
                portal_name: 'CPPP',
                portal_title: 'Central Public Procurement Portal (CPPP)',
                status: 'MOCK_FALLBACK',
                official_url: 'https://eprocure.gov.in',
                access_mode: 'Verified CPPP Structured Procurement Feed',
                blocker_details: 'CPPP enforces graphical session CAPTCHA',
                total_tenders_ingested: 3,
              },
              {
                portal_name: 'OPEN_GOV',
                portal_title: 'Open Government Data & PSU Feeds',
                status: 'ACTIVE',
                official_url: 'https://data.gov.in',
                access_mode: 'Open Government Data Public Procurement Catalog',
                total_tenders_ingested: 3,
              },
              {
                portal_name: 'TENDERKART',
                portal_title: 'TenderKart Client API Feed',
                status: 'MOCK_FALLBACK',
                official_url: 'https://tenderkart.in',
                access_mode: 'Verified Canonical Schema Feed',
                blocker_details: 'TenderKart Client API key (TENDERKART_API_KEY) not configured',
                total_tenders_ingested: 3,
              },
            ],
            latest_runs: [],
          }),
        });
        return;
      }

      // Check if filtered by source portal
      const isGemFilter = url.includes('source_portal=GEM');
      const isCpppFilter = url.includes('source_portal=CPPP');

      const allTenders = [
        {
          id: 't-gem-1',
          tender_reference: 'GEM/2026/B/892101',
          title: 'Supply and Commissioning of Industrial IoT Gateway Nodes',
          issuing_authority: 'Bharat Heavy Electricals Limited (BHEL)',
          sector: 'Industrial Electronics',
          estimated_budget_inr: 4850000,
          emd_amount_inr: 97000,
          msme_emd_exemption: true,
          submission_deadline: '2026-11-20T18:00:00Z',
          source_portal: 'GEM',
          source_tender_id: 'GEM-2026-B-892101',
          official_portal_url: 'https://bidplus.gem.gov.in/showbidDocument/GEM-2026-B-892101',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-10-21T00:00:00Z',
          updated_at: '2026-10-21T00:00:00Z',
        },
        {
          id: 't-cppp-1',
          tender_reference: 'CPPP/2026/NIC/789451',
          title: 'Modernization of Substation Switchgear Units',
          issuing_authority: 'National Thermal Power Corporation (NTPC)',
          sector: 'Electrical Infrastructure',
          estimated_budget_inr: 14500000,
          emd_amount_inr: 290000,
          msme_emd_exemption: true,
          submission_deadline: '2026-11-28T18:00:00Z',
          source_portal: 'CPPP',
          source_tender_id: '2026_NIC_789451_1',
          official_portal_url: 'https://eprocure.gov.in/eprocure/app?page=FrontEndTenderDetailsExternal&tenderId=2026_NIC_789451_1',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-10-21T00:00:00Z',
          updated_at: '2026-10-21T00:00:00Z',
        },
        {
          id: 't-opengov-1',
          tender_reference: 'OPENGOV/2026/IOCL/044',
          title: 'Supply of Precision Cryogenic Valves',
          issuing_authority: 'Indian Oil Corporation Limited (IOCL)',
          sector: 'Petrochemicals',
          estimated_budget_inr: 5600000,
          emd_amount_inr: 112000,
          msme_emd_exemption: true,
          submission_deadline: '2026-11-25T18:00:00Z',
          source_portal: 'OPEN_GOV',
          source_tender_id: 'OGD-PSU-IOCL-2026-044',
          official_portal_url: 'https://iocl.com/tenders/OGD-PSU-IOCL-2026-044',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-10-21T00:00:00Z',
          updated_at: '2026-10-21T00:00:00Z',
        },
        {
          id: 't-tenderkart-1',
          tender_reference: 'GEM/2026/B/902144',
          title: 'Supply and Commissioning of Grid-Tied Solar Inverters',
          issuing_authority: 'Power Grid Corporation of India Limited (PGCIL)',
          sector: 'Renewable Energy',
          estimated_budget_inr: 18500000,
          emd_amount_inr: 370000,
          msme_emd_exemption: true,
          submission_deadline: '2026-12-15T18:00:00Z',
          source_portal: 'TENDERKART',
          source_tender_id: 'c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c',
          official_portal_url: 'https://tenderkart.in/tenders/c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c',
          processing_status: 'PENDING',
          documents: [],
          created_at: '2026-10-21T00:00:00Z',
          updated_at: '2026-10-21T00:00:00Z',
        },
      ];

      let filtered = allTenders;
      if (isGemFilter) {
        filtered = allTenders.filter((t) => t.source_portal === 'GEM');
      } else if (isCpppFilter) {
        filtered = allTenders.filter((t) => t.source_portal === 'CPPP');
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: filtered,
          total: filtered.length,
          skip: 0,
          limit: 50,
        }),
      });
    });

    // 4. Navigate directly to /tenders
    await page.goto('/tenders');
    await page.waitForLoadState('networkidle');

    // 5. Verify Heading & Live Feeds Badge
    await expect(page.getByRole('heading', { name: 'Tender Opportunities' })).toBeVisible();
    await expect(page.getByText('Live Govt Feeds')).toBeVisible();

    // 6. Verify Government Source Badges are displayed
    await expect(page.getByTestId('badge-gem')).toBeVisible();
    await expect(page.getByTestId('badge-cppp')).toBeVisible();
    await expect(page.getByTestId('badge-opengov')).toBeVisible();
    await expect(page.getByTestId('badge-tenderkart')).toBeVisible();

    // 7. Verify Official Portal Notice External Links
    const portalLinks = page.locator('a:has-text("Portal Notice")');
    await expect(portalLinks.first()).toBeVisible();

    // 8. Verify Filter Tab Navigation
    const gemTab = page.locator('button:has-text("GeM Portal")');
    await gemTab.click();
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('GEM/2026/B/892101')).toBeVisible();
    await expect(page.getByText('CPPP/2026/NIC/789451')).not.toBeVisible();

    // 9. Refresh Button Execution
    const refreshBtn = page.getByRole('button', { name: 'Refresh Feed' });
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();
  });


  test('Journey 2: Administrator Government Ingestion Connectors Dashboard & Manual Sync Trigger', async ({ page }) => {
    // 1. Set Admin Session Storage Token
    await page.addInitScript(() => {
      sessionStorage.setItem('tender_bid_token', 'admin-token-11');
    });

    // 2. Mock Admin User
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'u-admin-01',
            email: 'admin@tenderbid.gov.in',
            full_name: 'Super Admin',
            role: 'ADMIN',
            is_active: true,
            created_at: '2026-10-01T00:00:00Z',
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

    // 3. Mock Ingestion Status Overview
    await page.route('**/api/v1/tenders/ingestion/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          scheduler_running: true,
          scheduler_interval_seconds: 3600,
          portals: [
            {
              portal_name: 'GEM',
              portal_title: 'Government e-Marketplace (GeM)',
              status: 'ACTIVE',
              official_url: 'https://gem.gov.in',
              access_mode: 'Verified GeM Procurement Feed',
              blocker_details: null,
              total_tenders_ingested: 4,
            },
            {
              portal_name: 'CPPP',
              portal_title: 'Central Public Procurement Portal (CPPP)',
              status: 'MOCK_FALLBACK',
              official_url: 'https://eprocure.gov.in',
              access_mode: 'Verified CPPP Structured Feed',
              blocker_details: 'CPPP enforces graphical session CAPTCHA',
              total_tenders_ingested: 3,
            },
            {
              portal_name: 'OPEN_GOV',
              portal_title: 'Open Government Data & PSU Feeds',
              status: 'ACTIVE',
              official_url: 'https://data.gov.in',
              access_mode: 'Public Procurement Open Catalog',
              blocker_details: null,
              total_tenders_ingested: 3,
            },
            {
              portal_name: 'TENDERKART',
              portal_title: 'TenderKart Client API Feed',
              status: 'MOCK_FALLBACK',
              official_url: 'https://tenderkart.in',
              access_mode: 'Verified Canonical Schema Feed',
              blocker_details: 'TenderKart Client API key (TENDERKART_API_KEY) not configured',
              total_tenders_ingested: 3,
            },
          ],
          latest_runs: [],
        }),
      });
    });

    // 4. Mock Ingestion Sync Trigger
    await page.route('**/api/v1/tenders/ingestion/sync', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'run-999',
          source_portal: 'ALL',
          status: 'SUCCESS',
          tenders_found: 10,
          tenders_ingested: 2,
          tenders_updated: 0,
          tenders_skipped: 8,
          started_at: '2026-10-21T18:00:00Z',
          completed_at: '2026-10-21T18:00:02Z',
        }),
      });
    });

    // 5. Mock /tenders list
    await page.route('**/api/v1/tenders?limit=100', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 't-admin-gem-1',
              tender_reference: 'GEM/2026/B/892101',
              title: 'Supply and Commissioning of Industrial IoT Gateway Nodes',
              issuing_authority: 'BHEL Electronics Division',
              sector: 'Industrial Electronics',
              processing_status: 'PENDING',
              source_portal: 'GEM',
              source_tender_id: 'GEM-2026-B-892101',
              documents: [],
              created_at: '2026-10-21T00:00:00Z',
              updated_at: '2026-10-21T00:00:00Z',
            },
          ],
          total: 1,
          skip: 0,
          limit: 100,
        }),
      });
    });

    // 6. Navigate to /admin/tenders
    await page.goto('/admin/tenders');
    await page.waitForLoadState('networkidle');

    // 7. Verify Ingestion Control Center Widget
    await expect(page.getByText('Government Tender Ingestion Connectors')).toBeVisible();
    await expect(page.getByText('Government e-Marketplace (GeM)')).toBeVisible();
    await expect(page.getByText('Central Public Procurement Portal (CPPP)')).toBeVisible();
    await expect(page.getByText('Open Government Data & PSU Feeds')).toBeVisible();
    await expect(page.getByText('TenderKart Client API Feed')).toBeVisible();

    // 8. Verify Ingestion Trigger Button & Success Toast
    const syncBtn = page.getByRole('button', { name: 'Sync All Portals Now' });
    await expect(syncBtn).toBeVisible();
    await syncBtn.click();

    await expect(page.getByText('Government sync complete!')).toBeVisible();
  });
});
