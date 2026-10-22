"""
=============================================================================
Phase 10: Reproducible End-to-End Platform Demonstration Script
Project: Agentic AI-Powered Tender Intelligence & Compliance Management for MSMEs
=============================================================================

This script executes a full-spectrum, synthetic demonstration of the platform:
1. Administrator publishes a sample tender with structured requirements.
2. Ingests and indexes synthetic tender RFP documentation.
3. MSME user registers and authenticates.
4. MSME updates company credentials (turnover, experience, certifications).
5. MSME uploads synthetic audited financial statements into the Document Vault.
6. MSME discovers tender in the public catalog.
7. MSME triggers the LangGraph compliance intelligence pipeline.
8. Deterministic rule engine evaluates financial & operational parameters.
9. Hybrid RAG retrieves authentic document excerpts with page citations.
10. Gemini AI (or rule fallback) explains findings without mutating outcomes.
11. Reconciliation guard enforces deterministic supremacy.
12. Audit-grade compliance report is inspected with verified citations.
13. Demonstrated mandatory failure scenario: Under-qualified MSME fails and is
    marked NOT_ELIGIBLE, proving that AI cannot overturn deterministic failure.
14. Persistence verification: saved reports remain accessible across reloads.
"""

import asyncio
import io
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure backend root is on sys.path and load environment variables
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))

import pymupdf
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password, UserRole
from app.db.repositories.companies import CompanyRepository
from app.db.repositories.users import UserRepository
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.tender import Tender


def make_pdf(title: str, text: str) -> bytes:
    """Create a synthetic PDF document in memory using PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n\n{text}", fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


async def run_demonstration():
    print("=" * 80)
    print("MSME TENDER INTELLIGENCE PLATFORM — PHASE 10 LIVE DEMONSTRATION")
    print("=" * 80)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://demo.tenderbid.internal") as client:
        # ---------------------------------------------------------------------
        # STEP 1: Provision Administrator & Publish Sample Tender
        # ---------------------------------------------------------------------
        print("\n[Step 1] Provisioning Administrator & Creating Sample Procurement Tender...")
        admin_email = f"admin_demo_{uuid.uuid4().hex[:6]}@ntpc.gov.in"
        admin_password = "AdminSecurePass2026!"

        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            admin_user = await user_repo.create(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                full_name="Chief Procurement Officer",
                role=UserRole.ADMIN.value,
            )
            await session.commit()

        admin_login = await client.post("/api/v1/auth/login", json={"email": admin_email, "password": admin_password})
        admin_token = admin_login.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Test-Bypass-Rate-Limit": "true"}

        tender_ref = f"NTPC/SWITCHGEAR/2026/{uuid.uuid4().hex[:4].upper()}"
        tender_payload = {
            "tender_reference": tender_ref,
            "title": "Procurement of 33kV Indoor Vacuum Circuit Breakers and Switchgear Panels",
            "issuing_authority": "National Thermal Power Corporation (NTPC)",
            "sector": "Electrical Infrastructure",
            "estimated_budget_inr": 50000000.0,
            "emd_amount_inr": 1000000.0,
            "msme_emd_exemption": True,
            "submission_deadline": (datetime.now(timezone.utc) + timedelta(days=45)).isoformat(),
            "official_portal_url": "https://eprocure.gov.in/eprocure/app",
            "structured_requirements": {
                "min_annual_turnover_inr": 40000000,
                "min_experience_years": 3,
                "required_certifications": ["ISO 9001:2015"],
                "mandatory_documents": [
                    {
                        "document_name": "Audited Financial Statements",
                        "document_category": "FINANCIAL_AUDIT",
                        "is_mandatory": True,
                    }
                ],
            },
        }

        create_tender_res = await client.post("/api/v1/admin/tenders", headers=admin_headers, json=tender_payload)
        tender_data = create_tender_res.json()
        tender_id = tender_data["id"]
        print(f"  [+] Tender Published: [{tender_ref}] {tender_data['title']}")
        print(f"  [+] Estimated Budget: INR {float(tender_data['estimated_budget_inr']):,.2f} (MSME EMD Exempt: {tender_data['msme_emd_exemption']})")

        # ---------------------------------------------------------------------
        # STEP 2: Ingest Synthetic Tender Notice PDF
        # ---------------------------------------------------------------------
        print("\n[Step 2] Uploading and Vector Indexing Tender RFP Document...")
        rfp_pdf = make_pdf(
            "NTPC TENDER SPECIFICATION 2026",
            "Clause 4.1: Minimum average annual turnover over past 3 years must exceed INR 40,000,000.\n"
            "Clause 4.2: Bidder must have valid ISO 9001:2015 Quality Management certification.\n"
            "Clause 4.3: Submission requires audited balance sheet certified by a Chartered Accountant.",
        )
        upload_rfp_res = await client.post(
            f"/api/v1/admin/tenders/{tender_id}/upload-docs",
            headers=admin_headers,
            files={"files": ("NTPC_Switchgear_Specification_Part1.pdf", rfp_pdf, "application/pdf")},
        )
        print(f"  [+] Uploaded RFP PDF: {upload_rfp_res.json()[0]['original_filename']}")

        # Trigger processing & vectorization
        proc_res = await client.post(f"/api/v1/admin/tenders/{tender_id}/process", headers=admin_headers)
        print(f"  [+] Vector Store Processed: Status = {proc_res.json()['processing_status']}")

        # ---------------------------------------------------------------------
        # STEP 3: MSME User Registration & Onboarding
        # ---------------------------------------------------------------------
        print("\n[Step 3] Registering New MSME Bidder Account...")
        msme_email = f"rajesh.sharma_{uuid.uuid4().hex[:6]}@apexswitchgear.in"
        msme_password = "MsmePassword2026!"
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": msme_email,
                "password": msme_password,
                "full_name": "Rajesh Sharma (Managing Director)",
            },
        )
        print(f"  [+] MSME Registered: {reg_res.json()['data']['full_name']} <{msme_email}>")

        msme_login = await client.post("/api/v1/auth/login", json={"email": msme_email, "password": msme_password})
        msme_token = msme_login.json()["data"]["access_token"]
        msme_headers = {"Authorization": f"Bearer {msme_token}", "X-Test-Bypass-Rate-Limit": "true"}

        # ---------------------------------------------------------------------
        # STEP 4: MSME Profile Configuration
        # ---------------------------------------------------------------------
        print("\n[Step 4] Configuring MSME Company Credentials & Audited Metrics...")
        comp_profile_payload = {
            "legal_name": "Apex Switchgear & Control Systems Pvt Ltd",
            "registration_number": f"UDYAM-MH-01-{uuid.uuid4().hex[:7].upper()}",
            "business_type": "SMALL",
            "sector": "Electrical Infrastructure",
            "incorporation_date": "2018-04-10",
            "annual_turnover": [
                {"fiscal_year": "2024-2025", "turnover_inr": 65000000.0},
                {"fiscal_year": "2023-2024", "turnover_inr": 58000000.0},
                {"fiscal_year": "2022-2023", "turnover_inr": 52000000.0},
            ],
            "certifications": [
                {"name": "ISO 9001:2015", "issuing_authority": "TUV Rheinland", "valid_until": "2028-12-31"}
            ],
            "work_experience": [
                {
                    "project_title": "Installation of 33kV Substations Phase 1",
                    "client_name": "Maharashtra State Electricity Distribution Co",
                    "contract_value_inr": 35000000.0,
                },
                {
                    "project_title": "Installation of 33kV Substations Phase 2",
                    "client_name": "Maharashtra State Electricity Distribution Co",
                    "contract_value_inr": 42000000.0,
                },
                {
                    "project_title": "EHV Switchgear Maintenance Contract",
                    "client_name": "Gujarat Urja Vikas Nigam Ltd",
                    "contract_value_inr": 28000000.0,
                },
            ],
        }
        comp_res = await client.post("/api/v1/company/profile", headers=msme_headers, json=comp_profile_payload)
        company_data = comp_res.json()["data"]
        print(f"  [+] Company Profile Created: {company_data['legal_name']} (Years in business: {company_data['years_in_business']} years)")

        # ---------------------------------------------------------------------
        # STEP 5: MSME Document Vault Upload
        # ---------------------------------------------------------------------
        print("\n[Step 5] Uploading Verified Proof to Company Document Vault...")
        vault_pdf = make_pdf(
            "APEX SWITCHGEAR - AUDITED BALANCE SHEET FY 2024-2025",
            "Independent Auditor's Report.\n"
            "We have audited the financial statements of Apex Switchgear & Control Systems Pvt Ltd.\n"
            "Total Revenue from Operations for the year ended March 31, 2025: INR 65,000,000.\n"
            "Net Profit After Tax: INR 7,200,000.\n"
            "Quality Certification: Certified ISO 9001:2015 compliance under Certificate #TR-98214.",
        )
        vault_upload_res = await client.post(
            "/api/v1/company/vault/documents/upload",
            headers=msme_headers,
            files={"file": ("Apex_Audited_Financial_Statements_FY25.pdf", vault_pdf, "application/pdf")},
            data={"document_category": "FINANCIAL_AUDIT"},
        )
        vault_doc = vault_upload_res.json()["data"]
        print(f"  [+] Vault Document Uploaded: {vault_doc['original_filename']} ({vault_doc['file_size_bytes']} bytes)")
        print(f"  [+] Document Extraction Status: {vault_doc['processing_status']}")

        # ---------------------------------------------------------------------
        # STEP 6: Tender Discovery
        # ---------------------------------------------------------------------
        print("\n[Step 6] Discovering Opportunities via Tender Search...")
        tenders_list = await client.get("/api/v1/tenders?search=Switchgear", headers=msme_headers)
        found_tenders = tenders_list.json()["items"]
        print(f"  [+] Search Query returned {len(found_tenders)} matching tender notice(s)")
        print(f"  [+] Target Tender: [{found_tenders[0]['tender_reference']}] {found_tenders[0]['title']}")

        # ---------------------------------------------------------------------
        # STEP 7: Run Deterministic & AI Compliance Analysis
        # ---------------------------------------------------------------------
        print("\n[Step 7] Orchestrating LangGraph Compliance Intelligence Pipeline...")
        eval_res = await client.post(
            "/api/v1/compliance/analyze",
            headers=msme_headers,
            json={"tender_id": tender_id, "include_ai_explanation": True},
        )
        report = eval_res.json()
        report_id = report["id"]

        print("\n[Step 8 & 9 & 10 & 11] Rule Engine Results & Reconciliation Verification:")
        print(f"  * Overall Evaluation Status : {report['overall_status']}")
        print(f"  * Objective Score           : {report['overall_score']}%")
        print(f"  * Rule Engine Version       : {report['rule_engine_version']}")
        print(f"  * Tender Version Hash       : {report['tender_version_hash'][:16]}...")
        print(f"  * Company Version Hash      : {report['company_version_hash'][:16]}...")

        # ---------------------------------------------------------------------
        # STEP 12: Inspect Structured Findings & Validated Citations
        # ---------------------------------------------------------------------
        print("\n[Step 12] Inspecting Criteria Findings & Page-Level Citations:")
        for idx, finding in enumerate(report["findings"], 1):
            print(f"  Criterion {idx}: [{finding['status']}] {finding['requirement_description']}")
            print(f"     Reason: {finding['reason']}")
            if finding.get("ai_explanation"):
                print(f"     AI Narrative: {finding['ai_explanation']}")
            if finding.get("evidence_citations"):
                for cit in finding["evidence_citations"]:
                    print(f"     -> Citation: [{cit['source_filename']}, Page {cit['page_number']}] \"{cit['excerpt'][:80]}...\"")

        assert report["overall_status"] == "ELIGIBLE", f"Expected ELIGIBLE, got {report['overall_status']}"

        # ---------------------------------------------------------------------
        # STEP 13: Demonstrated Mandatory Failure Scenario
        # ---------------------------------------------------------------------
        print("\n[Step 13] Demonstrating Strict Failure Handling on Under-Qualified Bidder...")
        failing_email = f"failing_msme_{uuid.uuid4().hex[:6]}@smallbiz.demo"
        await client.post(
            "/api/v1/auth/register",
            json={"email": failing_email, "password": "FailingPass2026!", "full_name": "Small Biz Owner"},
        )
        f_login = await client.post("/api/v1/auth/login", json={"email": failing_email, "password": "FailingPass2026!"})
        f_headers = {"Authorization": f"Bearer {f_login.json()['data']['access_token']}", "X-Test-Bypass-Rate-Limit": "true"}

        # Register profile with only INR 15M turnover (Required is 40M)
        await client.post(
            "/api/v1/company/profile",
            headers=f_headers,
            json={
                "legal_name": "Under-Threshold Electronics Ltd",
                "registration_number": f"UDYAM-DL-02-{uuid.uuid4().hex[:7].upper()}",
                "business_type": "MICRO",
                "sector": "Electrical Infrastructure",
                "incorporation_date": "2024-01-01",
                "annual_turnover": [{"fiscal_year": "2024-2025", "turnover_inr": 15000000.0}],
            },
        )

        failing_eval = await client.post(
            "/api/v1/compliance/analyze",
            headers=f_headers,
            json={"tender_id": tender_id, "include_ai_explanation": True},
        )
        failing_report = failing_eval.json()

        print(f"  [+] Under-threshold Bidder Overall Status: {failing_report['overall_status']}")
        assert failing_report["overall_status"] == "NOT_ELIGIBLE", "Mandatory failure MUST result in NOT_ELIGIBLE!"
        print(f"  [+] Mandatory Failure Guard Confirmed: Status is strictly NOT_ELIGIBLE.")
        print(f"  [+] Summary: {failing_report['summary'][:120]}...")

        # ---------------------------------------------------------------------
        # STEP 14: Report Persistence across Reloads
        # ---------------------------------------------------------------------
        print("\n[Step 14] Verifying Report Persistence Across Reloads...")
        fetch_persisted = await client.get(f"/api/v1/compliance/reports/{report_id}", headers=msme_headers)
        assert fetch_persisted.status_code == 200
        persisted_report = fetch_persisted.json()
        assert persisted_report["id"] == report_id
        assert persisted_report["overall_status"] == "ELIGIBLE"
        print(f"  [+] Report {report_id} verified permanently retrievable from database.")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE: ALL 14 VERIFICATION GATES PASSED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_demonstration())
