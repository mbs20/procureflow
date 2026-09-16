import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const API_BASE = "http://localhost:8000";
const DEV_API_KEY = "procureflow_dev_api_key_12345";
const headers = {
  "Content-Type": "application/json",
  "X-API-Key": DEV_API_KEY,
};

test.describe("Live Docker Phase 6 Decision & Award Workflow", () => {
  test("ScoringRun -> DecisionContext -> narrative -> grounding -> human revision -> Rank #2 rationale -> confirm -> superseded warning", async ({
    page,
    request,
  }) => {
    // 0. Verify live Docker backend is running
    let backendLive = false;
    try {
      const healthCheck = await request.get(`${API_BASE}/api/v1/health`, { timeout: 4000 });
      backendLive = healthCheck.status() === 200;
    } catch {
      backendLive = false;
    }
    test.skip(!backendLive, "Live Docker backend is not available on port 8000.");

    // 1. Create RFQ on live Docker stack
    const rfqRes = await request.post(`${API_BASE}/api/v1/rfqs`, {
      headers,
      data: {
        title: "Docker Live Phase 6 Evaluation & Human Award RFQ",
        description: "Live Docker Playwright test for Phase 6 end-to-end decision workflow",
        category: "Industrial",
        reference_currency: "USD",
        line_items: [
          { position: 1, description: "Hydraulic Pump 250BAR", quantity: 10, unit: "pcs" },
          { position: 2, description: "Filter Assembly", quantity: 20, unit: "pcs" },
        ],
        criteria: [
          { name: "Price", weight: 0.60, direction: "lower_is_better", data_type: "price" },
          { name: "Lead Time", weight: 0.40, direction: "lower_is_better", data_type: "days" },
        ],
      },
    });
    expect(rfqRes.status()).toBe(201);
    const rfq = await rfqRes.json();
    const rfqId = rfq.id;
    const item1Id = rfq.line_items[0].id;
    const item2Id = rfq.line_items[1].id;

    // 2. Ingest Supplier 1 (Rank 1: Cheaper and faster)
    const quote1Res = await request.post(`${API_BASE}/api/v1/quotations`, {
      headers,
      data: { rfq_id: rfqId, supplier_name: "Alpha Dynamics Inc" },
    });
    const qid1 = (await quote1Res.json()).id;
    const csvContent = "Item Description,Quantity,Unit,Unit Price,Currency,Total Price,Lead Time Days\nHydraulic Pump,10,pcs,500.00,USD,5000.00,14\nFilter Assembly,20,pcs,50.00,USD,1000.00,14\n";
    await request.post(`${API_BASE}/api/v1/quotations/${qid1}/documents`, {
      headers: { "X-API-Key": DEV_API_KEY },
      multipart: {
        file: { name: "quote1.csv", mimeType: "text/csv", buffer: Buffer.from(csvContent) },
      },
    });
    await request.post(`${API_BASE}/api/v1/quotations/${qid1}/extract`, { headers });
    
    // Poll for extraction completion
    let extr1: any = null;
    for (let i = 0; i < 20; i++) {
      const res = await request.get(`${API_BASE}/api/v1/quotations/${qid1}/extractions/latest`, { headers });
      if (res.status() === 200) {
        const body = await res.json();
        if (body.line_items && body.line_items.length >= 2) {
          extr1 = body;
          break;
        }
      }
      await page.waitForTimeout(500);
    }
    expect(extr1).not.toBeNull();

    await request.patch(`${API_BASE}/api/v1/quotations/${qid1}/line-items/${extr1.line_items[0].id}`, {
      headers,
      data: { rfq_line_item_id: item1Id, unit_price: 500.0, quantity: 10, total_price: 5000.0, currency: "USD", lead_time_days: 14 },
    });
    await request.patch(`${API_BASE}/api/v1/quotations/${qid1}/line-items/${extr1.line_items[1].id}`, {
      headers,
      data: { rfq_line_item_id: item2Id, unit_price: 50.0, quantity: 20, total_price: 1000.0, currency: "USD", lead_time_days: 14 },
    });
    await request.post(`${API_BASE}/api/v1/quotations/${qid1}/review-decision`, {
      headers,
      data: { status: "approved", decision_notes: "Approved Alpha" },
    });

    // 3. Ingest Supplier 2 (Rank 2: Higher cost, longer lead time)
    const quote2Res = await request.post(`${API_BASE}/api/v1/quotations`, {
      headers,
      data: { rfq_id: rfqId, supplier_name: "Beta Engineering Corp" },
    });
    const qid2 = (await quote2Res.json()).id;
    await request.post(`${API_BASE}/api/v1/quotations/${qid2}/documents`, {
      headers: { "X-API-Key": DEV_API_KEY },
      multipart: {
        file: { name: "quote2.csv", mimeType: "text/csv", buffer: Buffer.from(csvContent) },
      },
    });
    await request.post(`${API_BASE}/api/v1/quotations/${qid2}/extract`, { headers });
    
    let extr2: any = null;
    for (let i = 0; i < 20; i++) {
      const res = await request.get(`${API_BASE}/api/v1/quotations/${qid2}/extractions/latest`, { headers });
      if (res.status() === 200) {
        const body = await res.json();
        if (body.line_items && body.line_items.length >= 2) {
          extr2 = body;
          break;
        }
      }
      await page.waitForTimeout(500);
    }
    expect(extr2).not.toBeNull();

    await request.patch(`${API_BASE}/api/v1/quotations/${qid2}/line-items/${extr2.line_items[0].id}`, {
      headers,
      data: { rfq_line_item_id: item1Id, unit_price: 700.0, quantity: 10, total_price: 7000.0, currency: "USD", lead_time_days: 28 },
    });
    await request.patch(`${API_BASE}/api/v1/quotations/${qid2}/line-items/${extr2.line_items[1].id}`, {
      headers,
      data: { rfq_line_item_id: item2Id, unit_price: 75.0, quantity: 20, total_price: 1500.0, currency: "USD", lead_time_days: 28 },
    });
    await request.post(`${API_BASE}/api/v1/quotations/${qid2}/review-decision`, {
      headers,
      data: { status: "approved", decision_notes: "Approved Beta" },
    });

    // 4. Create ComparisonSnapshot
    const snapRes = await request.post(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/snapshots`, {
      headers,
      data: { title: "Phase 6 Docker Live Matrix Snapshot" },
    });
    expect(snapRes.status()).toBe(201);
    const snapId = (await snapRes.json()).id;

    // 5. Create ScoringConfiguration
    const cfgRes = await request.post(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/configurations`, {
      headers,
      data: {
        name: "Standard 60/40 Matrix Config",
        criteria: [
          { criterion_id: "c-price", name: "Total Price", weight: 0.60, direction: "lower_is_better", source_type: "price", source_field: "normalized_comparable_total" },
          { criterion_id: "c-lead", name: "Overall Lead Time", weight: 0.40, direction: "lower_is_better", source_type: "lead_time", source_field: "overall_lead_time_days" },
        ],
        normalization_method: "min_max",
        missing_value_policy: "block_scoring",
        tie_policy: "standard_competitive",
      },
    });
    expect(cfgRes.status()).toBe(201);
    const cfgId = (await cfgRes.json()).id;

    // 6. Execute Authoritative ScoringRun #1
    const run1Res = await request.post(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/runs`, {
      headers,
      data: { configuration_id: cfgId, snapshot_id: snapId, name: "Initial Scoring Run #1" },
    });
    expect(run1Res.status()).toBe(201);
    const run1 = await run1Res.json();
    const run1Id = run1.id;

    // 7. Generate Decision Narrative (mock provider)
    const narrRes = await request.post(`${API_BASE}/api/v1/rfqs/${rfqId}/decisions/narratives`, {
      headers,
      data: { scoring_run_id: run1Id, narrative_type: "decision_support_memo" },
    });
    expect(narrRes.status()).toBe(201);
    const narrative = await narrRes.json();
    expect(narrative.origin).toBe("ai_generated");
    expect(narrative.claims.length).toBeGreaterThan(0);

    // -------------------------------------------------------------------------
    // 8. Playwright UI Verification on Live Docker Application
    // -------------------------------------------------------------------------
    await page.goto(`/rfqs/${rfqId}/decisions`);

    // Verify main page heading and status
    await expect(page.locator("h1")).toContainText("Evidence-Backed Decision & Award Workflow");
    await expect(page.getByText("Human Decision Pending")).toBeVisible();

    // Verify narrative content
    await expect(page.getByText(/decision support memo #1/i)).toBeVisible();
    await expect(page.getByText("Alpha Dynamics Inc", { exact: true }).first()).toBeVisible();

    // Run WCAG accessibility check on live page
    const axeResults = await new AxeBuilder({ page })
      .disableRules(["color-contrast"]) // glassmorphism dark theme tokens
      .analyze();
    expect(axeResults.violations).toEqual([]);

    // 9. Inspect Grounded Claims Modal
    const claimRow = page.locator(".cursor-pointer").filter({ hasText: /Alpha Dynamics Inc achieved a total score/i }).first();
    await expect(claimRow).toBeVisible();
    await claimRow.click();
    await expect(page.getByText(/claim fact reference/i)).toBeVisible();
    await expect(page.getByText(/deterministic fact references:/i)).toBeVisible();
    await page.getByRole("button", { name: "Close" }).click();

    // 10. Human Revision Workflow (Append-Only)
    await page.getByRole("button", { name: "Revise Narrative" }).click();
    await expect(page.getByText("Create Human Revision")).toBeVisible();
    await page.locator("textarea[placeholder*='Enter corrected narrative']").fill("Procurement Committee Finding: Alpha Dynamics Inc is selected as Rank #1 vendor.");
    await page.locator("input[placeholder*='e.g. Corrected']").fill("Formally recorded committee summary.");
    await page.getByRole("button", { name: "Save Revision" }).click();

    // Verify revision is displayed
    await expect(page.getByText("Latest Human Revision")).toBeVisible();
    await expect(page.getByText("Formally recorded committee summary.")).toBeVisible();

    // 11. Award Selection with Rank #2 Mandatory Rationale Enforcement
    await page.getByRole("button", { name: "Draft & Confirm Award Decision" }).click();
    const modal = page.locator(".glass-panel").filter({ hasText: "Human Procurement Award Decision" });
    await expect(modal).toBeVisible();

    const confirmBtn = modal.getByRole("button", { name: "Confirm & Award RFQ" });
    await expect(confirmBtn).toBeDisabled();

    // Fill general justification
    await modal.locator("textarea[placeholder*='Provide commercial']").fill("Commercial review and risk assessment complete.");

    // Check all three governance checkboxes
    await modal.getByText("I have reviewed the deterministic scoring calculations").click();
    await modal.getByText("I confirm that technical compliance and commercial quotation").click();
    await modal.getByText("I understand this human action transitions the RFQ to DECIDED").click();

    // Select Beta Engineering Corp (Rank #2)
    await modal.getByText("Beta Engineering Corp", { exact: true }).click();

    // Non-Rank #1 governance warning is displayed
    await expect(page.getByText("Non-Rank #1 Selection Governance Rule")).toBeVisible();
    // Confirm button is STILL disabled without mandatory rationale
    await expect(confirmBtn).toBeDisabled();

    // Fill mandatory Non-Rank #1 rationale
    await modal.locator("textarea[placeholder*='Mandatory rationale for selecting non-Rank #1']").fill(
      "Strategic dual-source diversification and verified local manufacturing facility."
    );
    await expect(confirmBtn).toBeEnabled();

    // Confirm the Award
    await confirmBtn.click();
    await expect(page.getByText("Human Procurement Award Decision")).not.toBeVisible();

    // Verify Award status is now Confirmed
    await expect(page.getByText(/confirmed award/i)).toBeVisible();

    // 12. Create newer ScoringRun #2 on live backend to verify superseded warning
    const run2Res = await request.post(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/runs`, {
      headers,
      data: { configuration_id: cfgId, snapshot_id: snapId, name: "Superseding Scoring Run #2" },
    });
    expect(run2Res.status()).toBe(201);

    // Reload decision page to observe superseded warning
    await page.reload();
    await expect(page.getByText(/superseded/i)).toBeVisible();
  });
});
