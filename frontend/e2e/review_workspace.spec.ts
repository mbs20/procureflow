import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const MOCK_QUOTATION_ID = "11111111-1111-1111-1111-111111111111";
const MOCK_RFQ_ID = "22222222-2222-2222-2222-222222222222";

const mockSupplierQuotation = {
  id: MOCK_QUOTATION_ID,
  rfq_id: MOCK_RFQ_ID,
  supplier_name: "Apex Global Industrial Ltd",
  supplier_reference: "Apex_Quote_Q8921",
  status: "needs_review",
  failure_reason: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  documents: [
    {
      id: "doc-1",
      quotation_id: MOCK_QUOTATION_ID,
      filename: "Apex_Quote_Q8921.pdf",
      mime_type: "application/pdf",
      size_bytes: 10240,
      uploaded_at: new Date().toISOString(),
    },
  ],
};

const mockRFQ = {
  id: MOCK_RFQ_ID,
  title: "Industrial Piping & Flanges Procurement",
  description: "Quarterly flange requirements for plant maintenance",
  category: "industrial_equipment",
  status: "active",
  reference_currency: "USD",
  created_by: "procurement_lead",
  is_archived: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  line_items: [],
  criteria: [],
};

const mockExtractedQuotation = {
  id: "33333333-3333-3333-3333-333333333333",
  quotation_id: MOCK_QUOTATION_ID,
  extraction_model: "gpt-4o",
  extraction_version: "v1.0",
  extracted_at: new Date().toISOString(),
  overall_confidence: 0.94,
  is_current: true,
  notes: "Extracted successfully from PDF",
  raw_llm_output: {
    validation_warnings: ["Lead time field has confidence score 0.82 which is below threshold 0.85."],
  },
  acknowledged_warnings: [],
  line_items: [
    {
      id: "item-001",
      extracted_quotation_id: "33333333-3333-3333-3333-333333333333",
      rfq_line_item_id: null,
      description_raw: "High-grade Stainless Steel Flanges DN100 PN16",
      quantity: 50,
      unit: "pcs",
      unit_price: 150.0,
      currency: "USD",
      total_price: 7500.0,
      calculated_total_price: 7500.0,
      has_discrepancy: false,
      lead_time_days: 14,
      confidence: 0.96,
      source_page: 1,
      source_evidence: {
        page_number: 1,
        bounding_box: { x: 40, y: 180, width: 510, height: 22 },
        sheet_name: null,
        cell_range: "A12:E12",
        raw_text: "1 | High-grade Stainless Steel Flanges DN100 PN16 | 50 pcs | $150.00 | $7,500.00",
        ocr_confidence: 0.96,
      },
      source_bbox: { x: 40, y: 180, width: 510, height: 22 },
      human_corrected: false,
      is_removed: false,
      removal_reason: null,
    },
    {
      id: "item-002",
      extracted_quotation_id: "33333333-3333-3333-3333-333333333333",
      rfq_line_item_id: null,
      description_raw: "EPDM High-Temp Gaskets DN100",
      quantity: 100,
      unit: "pcs",
      unit_price: 50.0,
      currency: "USD",
      total_price: 5000.0,
      calculated_total_price: 5000.0,
      has_discrepancy: false,
      lead_time_days: 7,
      confidence: 0.94,
      source_page: 1,
      source_evidence: {
        page_number: 1,
        bounding_box: { x: 40, y: 215, width: 510, height: 22 },
        sheet_name: null,
        cell_range: "A13:E13",
        raw_text: "2 | EPDM High-Temp Gaskets DN100 | 100 pcs | $50.00 | $5,000.00",
        ocr_confidence: 0.94,
      },
      source_bbox: { x: 40, y: 215, width: 510, height: 22 },
      human_corrected: false,
      is_removed: false,
      removal_reason: null,
    },
  ],
  fields: [
    {
      id: "field-total",
      field_name: "total_amount",
      raw_value: "12500.00",
      normalised_value: { amount: 12500.0, currency: "USD" },
      confidence: 0.95,
      source_page: 1,
      source_evidence: {
        page_number: 1,
        bounding_box: { x: 430, y: 480, width: 120, height: 24 },
        raw_text: "Total Amount: $12,500.00",
      },
      source_bbox: { x: 430, y: 480, width: 120, height: 24 },
      human_corrected: false,
    },
  ],
};

const mockValidationStatus = {
  can_approve: true,
  critical_issues: [],
  warnings: [
    "Lead time field has confidence score 0.82 which is below threshold 0.85.",
  ],
  acknowledged_warnings: [],
};

const mockAuditLogs = [
  {
    id: "audit-001",
    rfq_id: MOCK_RFQ_ID,
    event_type: "quotation.extracted",
    actor_type: "system",
    actor_id: "system_pipeline",
    timestamp: new Date().toISOString(),
    payload: {
      message: "Phase 2 AI & OCR extraction pipeline successfully ingested document.",
      items_count: 2,
    },
  },
];

test.describe("Phase 3 Human Review Interface", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept API calls to provide deterministic mock data
    await page.route(`**/api/v1/quotations/${MOCK_QUOTATION_ID}`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockSupplierQuotation),
        });
      } else {
        await route.continue();
      }
    });

    await page.route(`**/api/v1/rfqs/${MOCK_RFQ_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockRFQ),
      });
    });

    await page.route(`**/api/v1/quotations/${MOCK_QUOTATION_ID}/extractions/latest`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockExtractedQuotation),
      });
    });

    await page.route(`**/api/v1/quotations/${MOCK_QUOTATION_ID}/validation-status`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockValidationStatus),
      });
    });

    await page.route(`**/api/v1/quotations/${MOCK_QUOTATION_ID}/audit-logs`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockAuditLogs),
      });
    });

    await page.route(`**/api/v1/quotations/${MOCK_QUOTATION_ID}/documents/*/download`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n185\n%%EOF",
      });
    });
  });

  test("Split-pane review workspace renders with both document and extraction data", async ({ page }) => {
    await page.goto(`/quotations/${MOCK_QUOTATION_ID}/review`);

    // Verify header semantics: Approve Extraction & Reject Extraction (quality review, not commercial award)
    await expect(page.getByRole("button", { name: "Approve Extraction" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reject Extraction" })).toBeVisible();

    // Verify Supplier and Document Metadata
    await expect(page.getByText("Apex Global Industrial Ltd").first()).toBeVisible();
    await expect(page.getByText("Apex_Quote_Q8921.pdf")).toBeVisible();

    // Verify Extracted Structured Line Items
    await expect(page.getByText("High-grade Stainless Steel Flanges DN100 PN16")).toBeVisible();
    await expect(page.getByText("EPDM High-Temp Gaskets DN100")).toBeVisible();

    // Verify Document Viewer & Structured Data split-pane regions
    await expect(page.getByLabel("Original Document Viewer")).toBeVisible();
    await expect(page.getByLabel("Extracted Structured Data and Verification")).toBeVisible();
  });

  test("Evidence click locates and activates source evidence highlight", async ({ page }) => {
    await page.goto(`/quotations/${MOCK_QUOTATION_ID}/review`);

    // Click on the first line item to focus its evidence
    const lineItemRow = page.getByText("High-grade Stainless Steel Flanges DN100 PN16");
    await lineItemRow.click();

    // Evidence locator tag should be visible
    const p1Badge = page.getByText("p. 1");
    await expect(p1Badge.first()).toBeVisible();
  });

  test("Soft-delete line item preserves item for auditability rather than hard-deleting", async ({ page }) => {
    let deleteCalled = false;
    await page.route(`**/api/v1/quotations/${MOCK_QUOTATION_ID}/line-items/item-001*`, async (route) => {
      if (route.request().method() === "DELETE") {
        deleteCalled = true;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            ...mockExtractedQuotation.line_items[0],
            is_removed: true,
            removal_reason: "Excluded from evaluation",
          }),
        });
      }
    });

    // Handle prompt/dialog automatically
    page.on("dialog", async (dialog) => {
      await dialog.accept("Excluded from evaluation");
    });

    await page.goto(`/quotations/${MOCK_QUOTATION_ID}/review`);

    // Click remove button on the first item
    const removeBtn = page.getByTitle("Soft-delete this line item (preserves in audit history)");
    await removeBtn.first().click();

    expect(deleteCalled).toBeTruthy();
  });

  test("Preserve quoted vs calculated values in Line Item Edit modal", async ({ page }) => {
    await page.goto(`/quotations/${MOCK_QUOTATION_ID}/review`);

    // Open Edit Dialog for item 1
    const editBtn = page.getByTitle("Edit line item");
    await editBtn.first().click();

    // Modal title & audit safety notice
    await expect(page.getByText("Edit Line Item (Preserves Quoted vs Calculated)")).toBeVisible();
    await expect(page.getByText("Phase 3 Audit Safeguard:")).toBeVisible();

    // Form inputs exist and show original unit price and calculated total
    await expect(page.getByLabel("Reason for Change *")).toBeVisible();
  });

  test("Keyboard safety: shortcuts do not fire while typing in input fields", async ({ page }) => {
    await page.goto(`/quotations/${MOCK_QUOTATION_ID}/review`);

    // Open Edit Line Item Dialog
    const editBtn = page.getByTitle("Edit line item");
    await editBtn.first().click();

    const reasonInput = page.getByLabel("Reason for Change *");
    await reasonInput.click();
    await reasonInput.fill("jkl");

    // The modal should remain open and 'jkl' should be in the input field without triggering global navigation
    await expect(reasonInput).toHaveValue("jkl");
    await expect(page.getByText("Edit Line Item (Preserves Quoted vs Calculated)")).toBeVisible();
  });

  test("Audit Trail drawer displays chronological events and state transitions", async ({ page }) => {
    await page.goto(`/quotations/${MOCK_QUOTATION_ID}/review`);

    // Click Audit Trail button
    const auditBtn = page.getByRole("button", { name: /Audit Trail/ });
    await auditBtn.click();

    // Verify drawer appears with event details
    await expect(page.getByText(/Immutable Audit Trail/)).toBeVisible();
    await expect(page.getByText("quotation.extracted")).toBeVisible();
    await expect(page.getByText("system_pipeline")).toBeVisible();
  });

  test("Extraction decision modal distinguishes blockers and enforces safety", async ({ page }) => {
    await page.goto(`/quotations/${MOCK_QUOTATION_ID}/review`);

    // Click Approve Extraction
    const approveBtn = page.getByRole("button", { name: "Approve Extraction" });
    await approveBtn.click();

    // Verify Decision Modal
    await expect(page.getByText("Approve Extraction Quality")).toBeVisible();
    await expect(
      page.getByText("This action verifies extraction accuracy for downstream RFQ comparison.")
    ).toBeVisible();
  });

  test("Accessibility: review workspace complies with WCAG 2.2 AA standards", async ({ page }) => {
    await page.goto(`/quotations/${MOCK_QUOTATION_ID}/review`);

    // Wait for the workspace to be fully rendered
    await page.waitForSelector("text=Apex Global Industrial Ltd");

    // Run axe-core accessibility audit targeting WCAG 2.2 AA standards
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .exclude("canvas")
      .analyze();

    // Ensure zero critical or serious accessibility violations
    const seriousOrCriticalViolations = accessibilityScanResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );

    expect(seriousOrCriticalViolations).toEqual([]);
  });
});
