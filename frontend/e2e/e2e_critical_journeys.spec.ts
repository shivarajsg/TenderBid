import { test, expect } from '@playwright/test';

test.describe('Original Phase 10: Critical Full-Stack User Journeys', () => {

  // -------------------------------------------------------------------------
  // Journey 1: Authentication & Route Protection
  // -------------------------------------------------------------------------
  test('Journey 1: Authentication, Protected Route Redirection, Dashboard & Logout', async ({ page }) => {
    // Mock login and auth routes BEFORE navigation
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            access_token: 'fake-jwt-msme-token',
            token_type: 'bearer',
            expires_in: 3600,
          },
        }),
      });
    });

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'u-msme-01',
            email: 'msme_owner@example.com',
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
            registration_number: 'UDYAM-DL-01-0001',
            business_type: 'MICRO',
            sector: 'Electrical Infrastructure',
            incorporation_date: '2020-01-01',
            annual_turnover: [],
            certifications: [],
            work_experience: [],
            created_at: '2026-10-01T00:00:00Z',
            updated_at: '2026-10-01T00:00:00Z',
          },
        }),
      });
    });

    await page.route('**/api/v1/notifications/unread-count', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ unread_count: 2 }),
      });
    });

    await page.route('**/api/v1/tenders*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    await page.route('**/api/v1/company/vault/documents*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] }),
      });
    });

    await page.route('**/api/v1/compliance/reports*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    // 1. Visit protected dashboard without authenticating -> should redirect to /login
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/.*\/login/);

    // 2. Fill login form
    await page.waitForSelector('input[type="email"]');
    await page.locator('input[type="email"]').fill('msme_owner@example.com');
    await page.locator('input[type="password"]').fill('CorrectPassword123!');
    await page.locator('button[type="submit"]').click();

    // 3. Assert dashboard renders authenticated context
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.locator('text=Welcome back, Rajesh Sharma')).toBeVisible();
    await expect(page.locator('text=Sharma Electricals Pvt Ltd')).toBeVisible();

    // 4. Test logout
    await page.locator('button[title="Sign Out"]').click();
    await expect(page).toHaveURL(/.*\/login/);

    // 5. Verify protected pages redirect back to login
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/.*\/login/);
  });

  // -------------------------------------------------------------------------
  // Journey 2: Administrator Tender Processing & Review
  // -------------------------------------------------------------------------
  test('Journey 2: Administrator Tender Processing, Extraction & Approval Controls', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('tender_bid_token', 'admin-token');
    });

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            id: 'admin-01',
            email: 'cpo@gov.internal',
            full_name: 'Chief Procurement Officer',
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

    const sampleBundle = {
      tender_id: 't-admin-1',
      extraction_status: 'NEEDS_REVIEW',
      criteria: [
        {
          criterion_type: 'ANNUAL_TURNOVER',
          title: 'Minimum Annual Turnover',
          extracted_value: { minimum_annual_turnover_inr: 40000000.0 },
          source_filename: 'NIT_Document.pdf',
          page_number: 3,
          supporting_excerpt: 'Minimum annual turnover of INR 4.0 Crores is required.',
          status: 'NEEDS_REVIEW',
          confidence: 0.85,
          review_notes: 'Potential ambiguity: Page 3 states 4 Cr, Section 4 states 5 Cr.',
        },
      ],
      conflicts: ['Potential ambiguity detected: Page 3 specifies 4 Cr, Page 12 mentions 5 Cr for consortiums.'],
      unsupported_clauses: [],
      extracted_at: '2026-10-21T10:00:00Z',
    };

    const sampleTenders = [
      {
        id: 't-admin-1',
        tender_reference: 'NTPC/2026/BAT/01',
        title: 'BESS Battery Energy Storage System Supply',
        issuing_authority: 'NTPC Limited',
        sector: 'Renewable Energy',
        estimated_budget: 85000000.0,
        emd_amount: 1700000.0,
        submission_deadline: '2026-12-15T18:00:00Z',
        processing_status: 'READY',
        requirements_approval_status: 'NEEDS_REVIEW',
        documents_count: 2,
        chunks_count: 45,
        proposed_requirements: sampleBundle,
        documents: [],
        created_at: '2026-10-01T00:00:00Z',
        updated_at: '2026-10-01T00:00:00Z',
      },
    ];

    await page.route('**/api/v1/tenders*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: sampleTenders, total: 1 }),
      });
    });

    await page.route('**/api/v1/tenders/ingestion/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          scheduler_running: true,
          scheduler_interval_seconds: 3600,
          portals: [],
          latest_runs: [],
        }),
      });
    });

    await page.route('**/api/v1/admin/tenders/t-admin-1/proposed-requirements', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(sampleBundle),
      });
    });

    await page.goto('/admin/tenders');
    await expect(page.locator('text=Admin Tender Management')).toBeVisible();
    await expect(page.locator('text=NTPC/2026/BAT/01')).toBeVisible();

    // Verify Review Criteria button exists
    const reviewBtn = page.locator('button:has-text("Review Criteria")');
    await expect(reviewBtn).toBeVisible();
    await reviewBtn.click();

    // Verify Review Modal opens with extraction details and conflict indicators
    await expect(page.locator('text=Review & Approve Extracted Criteria')).toBeVisible();
    await expect(page.locator('text=Detected Conflicts / Review Needed:')).toBeVisible();
    await expect(page.locator('text=Potential ambiguity detected')).toBeVisible();
    await expect(page.locator('button:has-text("Approve & Make Authoritative")')).toBeVisible();
    await expect(page.locator('button:has-text("Reject Criteria")')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Journey 3: MSME Document Vault & Compliance Analysis
  // -------------------------------------------------------------------------
  test('Journey 3: MSME Document Vault, Catalog Discovery & Compliance Analysis', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('tender_bid_token', 'msme-token');
    });

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'u-1', email: 'msme@test.com', full_name: 'MSME Bidder', role: 'MSME_USER', is_active: true, created_at: '2026-10-01T00:00:00Z' },
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
            id: 'comp-1',
            owner_id: 'u-1',
            legal_name: 'Solar Tech Solutions Ltd',
            registration_number: 'UDYAM-MH-02-1234',
            business_type: 'SMALL',
            sector: 'Renewable Energy',
            incorporation_date: '2019-01-01',
            annual_turnover: [],
            certifications: [],
            work_experience: [],
            created_at: '2026-10-01T00:00:00Z',
            updated_at: '2026-10-01T00:00:00Z',
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

    await page.route('**/api/v1/company/vault/documents*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: [
            {
              id: 'doc-v-1',
              company_id: 'comp-1',
              document_category: 'AUDITED_BALANCE_SHEET',
              original_filename: 'FY24_BalanceSheet.pdf',
              file_size_bytes: 1048576,
              mime_type: 'application/pdf',
              verification_status: 'VERIFIED',
              sha256_hash: 'abcdef0123456789abcdef0123456789',
              indexed_chunks: 12,
              total_pages: 8,
              processing_status: 'COMPLETED',
              created_at: '2026-10-01T10:00:00Z',
            },
          ],
        }),
      });
    });

    // 1. Visit Vault
    await page.goto('/vault');
    await expect(page.locator('text=Company Document Vault')).toBeVisible();
    await expect(page.locator('text=FY24_BalanceSheet.pdf')).toBeVisible();

    // 2. Visit Tender Discovery
    const sampleSolarTender = {
      id: 't-solar-1',
      tender_reference: 'SECI/SOLAR/2026/04',
      title: '50MW Grid-Connected Solar PV Project',
      issuing_authority: 'Solar Energy Corporation of India',
      sector: 'Renewable Energy',
      estimated_budget: 120000000.0,
      submission_deadline: '2026-11-30T17:00:00Z',
      processing_status: 'READY',
      documents: [],
      created_at: '2026-10-01T00:00:00Z',
      updated_at: '2026-10-01T00:00:00Z',
    };

    await page.route('**/api/v1/tenders*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [sampleSolarTender],
          total: 1,
        }),
      });
    });

    await page.goto('/tenders');
    await expect(page.locator('text=SECI/SOLAR/2026/04')).toBeVisible();
    await expect(page.locator('text=50MW Grid-Connected Solar PV Project')).toBeVisible();

    // 3. Navigate to Compliance Analysis
    const sampleReport = {
      id: 'rep-e2e-1',
      tender_id: 't-solar-1',
      company_id: 'comp-1',
      overall_status: 'ELIGIBLE',
      overall_score: 95.0,
      summary: 'The MSME meets all financial turnover, domain experience and active ISO certification requirements.',
      findings: [
        {
          id: 'f-1',
          rule_type: 'ANNUAL_TURNOVER',
          requirement_id: 'req_turnover',
          requirement_description: 'Minimum turnover requirement INR 4.0 Cr',
          status: 'PASS',
          is_mandatory: true,
          reason: 'Company turnover satisfies tender condition.',
          observed_value: { turnover: 50000000 },
          required_value: { minimum_inr: 40000000 },
          evidence_citations: [],
          created_at: '2026-10-21T12:00:00Z',
        },
      ],
      created_at: '2026-10-21T12:00:00Z',
    };

    await page.route('**/api/v1/compliance/analyze', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(sampleReport),
      });
    });

    await page.route('**/api/v1/compliance/reports/rep-e2e-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(sampleReport),
      });
    });

    await page.goto('/compliance/analyze');
    await expect(page.locator('text=Run Tender Compliance Analysis')).toBeVisible();
    await expect(page.locator('text=Deterministic Architecture Guarantee')).toBeVisible();

    // Run compliance
    await page.locator('button:has-text("Start Compliance Evaluation")').click();

    // Verify redirected to report detail
    await expect(page).toHaveURL(/.*\/compliance\/reports\/rep-e2e-1/);
    await expect(page.locator('text=Authoritative Evaluation')).toBeVisible();
    await expect(page.locator('text=95%')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Journey 4: Contextual Tender Q&A & Ungrounded Question Guard
  // -------------------------------------------------------------------------
  test('Journey 4: Tender Q&A with Verified Citations & Insufficient Evidence Guard', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('tender_bid_token', 'msme-token');
    });

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'u-1', email: 'msme@test.com', full_name: 'MSME User', role: 'MSME_USER', is_active: true, created_at: '2026-10-01T00:00:00Z' },
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

    await page.route('**/api/v1/tenders/t-qa-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 't-qa-1',
          tender_reference: 'QA/TENDER/2026',
          title: 'Substation Automation RFP',
          issuing_authority: 'PowerGrid Corp',
          sector: 'Electrical',
          estimated_budget: 35000000.0,
          submission_deadline: '2026-12-01T10:00:00Z',
          processing_status: 'READY',
          documents: [
            {
              id: 'doc-qa-1',
              original_filename: 'Substation_Specs_RFP.pdf',
              file_size_bytes: 2048000,
              created_at: '2026-10-10T10:00:00Z',
            },
          ],
          created_at: '2026-10-01T00:00:00Z',
          updated_at: '2026-10-01T00:00:00Z',
        }),
      });
    });

    // 1. Visit tender detail page
    await page.goto('/tenders/t-qa-1');
    await expect(page.locator('text=Substation Automation RFP')).toBeVisible();

    // 2. Contextual Tender Q&A drawer is visible
    await expect(page.locator('text=Contextual Tender Q&A')).toBeVisible();

    // 3. Ask a supported question
    await page.route('**/api/v1/tenders/t-qa-1/qa', async (route) => {
      const payload = JSON.parse(route.request().postData() || '{}');
      if (payload.question.includes('warranty')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tender_id: 't-qa-1',
            question: payload.question,
            answer: 'A comprehensive 5-year onsite replacement warranty is required under Clause 14.2.',
            status: 'ANSWERED',
            confidence: 'HIGH',
            citations: [
              {
                document_id: 'doc-qa-1',
                source_filename: 'Substation_Specs_RFP.pdf',
                page_number: 14,
                supporting_excerpt: 'Clause 14.2: Comprehensive 5-year onsite replacement warranty is mandatory.',
              },
            ],
          }),
        });
      } else {
        // Ungrounded question
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tender_id: 't-qa-1',
            question: payload.question,
            answer: 'The attached tender notices and RFP documents do not contain verifiable information answering this query.',
            status: 'INSUFFICIENT_EVIDENCE',
            confidence: 'LOW',
            citations: [],
          }),
        });
      }
    });

    const qInput = page.locator('input[placeholder*="What is the required turnover"]');
    await qInput.fill('What is the required warranty period?');
    await page.getByRole('button', { name: 'Ask Question', exact: true }).click();

    // Assert grounded evidence citation appears
    await expect(page.locator('text=Grounded Evidence Verified')).toBeVisible();
    await expect(page.locator('text=5-year onsite replacement warranty').first()).toBeVisible();
    await expect(page.locator('text=Substation_Specs_RFP.pdf').first()).toBeVisible();
    await expect(page.locator('text=Page 14')).toBeVisible();

    // 4. Ask an ungrounded question (insufficient evidence guard)
    await qInput.fill('What are the rules regarding catering?');
    await page.getByRole('button', { name: 'Ask Question', exact: true }).click();

    // Assert insufficient evidence guard banner appears
    await expect(page.locator('text=Insufficient Evidence in Tender')).toBeVisible();
    await expect(page.locator('text=do not contain verifiable information')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Journey 5: Bid Pipeline Tracking & Persisted Alerts
  // -------------------------------------------------------------------------
  test('Journey 5: Bid Preparation Pipeline Stage Management & Notification Center', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('tender_bid_token', 'msme-token');
    });

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'u-1', email: 'msme@pipeline.test', full_name: 'Pipeline User', role: 'MSME_USER', is_active: true, created_at: '2026-10-01T00:00:00Z' },
        }),
      });
    });

    let currentStage = 'PREPARING';

    await page.route(/\/api\/v1\/applications/, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            items: [
              {
                id: 'app-01',
                company_id: 'comp-1',
                tender_id: 't-pipe-1',
                status: currentStage,
                notes: 'Assembling audited financial proofs.',
                tender_title: 'Smart Metering Infrastructure Project',
                tender_reference: 'DISCOM/AMI/2026/09',
                submission_deadline: '2026-11-20T17:00:00Z',
                estimated_budget_inr: 45000000.0,
                created_at: '2026-10-15T12:00:00Z',
                updated_at: '2026-10-15T12:00:00Z',
              },
            ],
            total: 1,
          }),
        });
      } else if (route.request().method() === 'PATCH') {
        const payload = JSON.parse(route.request().postData() || '{}');
        currentStage = payload.status || 'READY';
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'app-01',
            company_id: 'comp-1',
            tender_id: 't-pipe-1',
            status: currentStage,
            notes: 'Marked ready for submission.',
            tender_title: 'Smart Metering Infrastructure Project',
            tender_reference: 'DISCOM/AMI/2026/09',
            submission_deadline: '2026-11-20T17:00:00Z',
            estimated_budget_inr: 45000000.0,
            created_at: '2026-10-15T12:00:00Z',
            updated_at: '2026-10-15T12:00:00Z',
          }),
        });
      }
    });

    // Mock Notification Bell & List
    await page.route('**/api/v1/notifications/unread-count', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ unread_count: 1 }),
      });
    });

    await page.route('**/api/v1/notifications*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'notif-01',
              company_id: 'comp-1',
              tender_id: 't-pipe-1',
              notification_type: 'DEADLINE_48H',
              title: 'Deadline Approaching: DISCOM/AMI/2026/09',
              message: 'Tender closes in 24 hours. Ensure all required proofs are submitted.',
              is_read: false,
              created_at: '2026-10-21T08:00:00Z',
            },
          ],
          total: 1,
          unread_count: 1,
        }),
      });
    });

    // 1. Visit Applications Pipeline page
    await page.goto('/applications');
    await expect(page.locator('text=Bid Preparation Pipeline')).toBeVisible();
    await expect(page.locator('text=Smart Metering Infrastructure Project')).toBeVisible();
    await expect(page.locator('text=DISCOM/AMI/2026/09')).toBeVisible();

    // 2. Advance stage from PREPARING -> READY
    const advanceBtn = page.locator('button:has-text("→ READY")');
    await expect(advanceBtn).toBeVisible();
    await advanceBtn.click();

    // Verify stage advanced: button to advance to SUBMITTED appears
    await expect(page.locator('button:has-text("→ SUBMITTED")')).toBeVisible();

    // 3. Check Navbar Notification Bell
    const bellBtn = page.locator('button[aria-label="Notifications"]');
    await expect(bellBtn).toBeVisible();
    await expect(bellBtn.locator('text=1')).toBeVisible();

    // Click bell to open notifications dropdown
    await bellBtn.click();
    await expect(page.locator('text=Deadline Approaching: DISCOM/AMI/2026/09')).toBeVisible();
  });

  // -------------------------------------------------------------------------
  // Journey 6: Report Display, Verified Citations & Security Isolation
  // -------------------------------------------------------------------------
  test('Journey 6: Compliance Report Distinct Status Badges, Citations & RBAC Barrier', async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem('tender_bid_token', 'msme-token');
    });

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { id: 'u-1', email: 'msme@security.test', full_name: 'Security Tester', role: 'MSME_USER', is_active: true, created_at: '2026-10-01T00:00:00Z' },
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

    // Report with mixed statuses: PASS, FAIL, MISSING_EVIDENCE
    await page.route('**/api/v1/compliance/reports/rep-audit-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'rep-audit-1',
          tender_id: 't-audit-1',
          company_id: 'comp-1',
          overall_status: 'NOT_ELIGIBLE',
          overall_score: 42.0,
          summary: 'MSME is NOT ELIGIBLE due to mandatory turnover deficit and missing GST documentation.',
          created_at: '2026-10-21T14:00:00Z',
          findings: [
            {
              id: 'f-1',
              rule_type: 'ANNUAL_TURNOVER',
              requirement_id: 'req_turnover',
              requirement_description: 'Minimum annual turnover INR 5.0 Cr',
              status: 'FAIL',
              is_mandatory: true,
              reason: 'Turnover INR 2.5 Cr is below required INR 5.0 Cr.',
              required_value: { required_inr: 50000000 },
              observed_value: { company_turnover_inr: 25000000 },
              evidence_citations: [
                {
                  evidence_id: 'ev-1',
                  source_type: 'TENDER_DOCUMENT',
                  document_id: 'doc-1',
                  source_filename: 'Tender_Notice_NIT.pdf',
                  page_number: 4,
                  excerpt: 'Minimum annual turnover of INR 5.0 Crores is required in last 3 financial years.',
                  retrieval_method: 'HYBRID_FUSION',
                  relevance_score: 0.94,
                },
              ],
              created_at: '2026-10-21T14:00:00Z',
            },
            {
              id: 'f-2',
              rule_type: 'MANDATORY_DOCUMENT',
              requirement_id: 'req_gst',
              requirement_description: 'Valid GSTIN Certificate mandatory',
              status: 'MISSING_EVIDENCE',
              is_mandatory: true,
              reason: 'No GST certificate found in company vault.',
              required_value: { required_document: 'GSTIN Registration Certificate' },
              observed_value: null,
              evidence_citations: [],
              created_at: '2026-10-21T14:00:00Z',
            },
            {
              id: 'f-3',
              rule_type: 'CERTIFICATION',
              requirement_id: 'req_iso',
              requirement_description: 'ISO 9001:2015 Quality Certificate',
              status: 'PASS',
              is_mandatory: false,
              reason: 'Valid ISO 9001:2015 certificate verified in vault.',
              required_value: { certification_code: 'ISO 9001:2015' },
              observed_value: { certification_code: 'ISO 9001:2015', valid_until: '2028-12-31' },
              evidence_citations: [],
              created_at: '2026-10-21T14:00:00Z',
            },
          ],
        }),
      });
    });

    // 1. Visit Report Detail Page
    await page.goto('/compliance/reports/rep-audit-1');
    await expect(page.locator('text=Authoritative Evaluation')).toBeVisible();

    // Verify Prominent NOT_ELIGIBLE Status Badge
    await expect(page.locator('[data-testid="status-badge-not_eligible"]')).toBeVisible();
    await expect(page.locator('text=42%')).toBeVisible();

    // Verify distinct criteria statuses rendered
    await expect(page.locator('[data-testid="status-badge-fail"]')).toBeVisible();
    await expect(page.locator('[data-testid="status-badge-missing_evidence"]')).toBeVisible();
    await expect(page.locator('[data-testid="status-badge-pass"]')).toBeVisible();

    // Verify authentic citation excerpt and page number
    await expect(page.locator('text=Tender_Notice_NIT.pdf')).toBeVisible();
    await expect(page.locator('text=Page 4')).toBeVisible();
    await expect(page.locator('text=Minimum annual turnover of INR 5.0 Crores')).toBeVisible();

    // 2. Security Test: Attempt visiting Admin Route with MSME role
    await page.goto('/admin/tenders');
    // Must be blocked and redirected to dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
  });
});
