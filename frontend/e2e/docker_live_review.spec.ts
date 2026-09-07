import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

const API_BASE = "http://localhost:8000";
const DEV_API_KEY = "procureflow_dev_api_key_12345";
const headers = {
  "Content-Type": "application/json",
  "X-API-Key": DEV_API_KEY,
};

test.describe("Live Docker Human Review Workflow", () => {
  test("document review -> evidence navigation -> human correction -> approval against live Docker stack", async ({
    page,
    request,
  }) => {
    // Verify live backend availability; skip gracefully if running in a standalone frontend CI runner
    let backendLive = false;
    try {
      const healthCheck = await request.get(`${API_BASE}/api/v1/health`, { timeout: 3000 });
      backendLive = healthCheck.status() === 200;
    } catch {
      backendLive = false;
    }
    test.skip(!backendLive, "Live Docker backend is not available on port 8000 (standalone CI mode).");

    // 1. Create RFQ on live Docker backend
    const rfqRes = await request.post(`${API_BASE}/api/v1/rfqs`, {
      headers,
      data: {
        title: "Docker Live Pipeline Flanges",
        category: "Piping",
        reference_currency: "USD",
        line_items: [
          {
            position: 1,
            description: "High Pressure Flange DN100",
            quantity: 20,
            unit: "pcs",
          },
        ],
        criteria: [
          { name: "Total Price", weight: 1.0, criterion_type: "price", is_mandatory: true },
        ],
      },
    });
    expect(rfqRes.status()).toBe(201);
    const rfq = await rfqRes.json();
    const rfqId = rfq.id;

    // 2. Create Quotation on live backend
    const quoteRes = await request.post(`${API_BASE}/api/v1/quotations`, {
      headers,
      data: {
        rfq_id: rfqId,
        supplier_name: "Docker Test Industries Ltd",
        supplier_reference: "DOCKER-Q100",
      },
    });
    expect(quoteRes.status()).toBe(201);
    const quote = await quoteRes.json();
    const quoteId = quote.id;

    // 3. Upload a CSV quotation document
    const csvContent =
      "Item Description,Quantity,Unit,Unit Price,Currency,Total Price,Lead Time Days\n" +
      "High Pressure Flange DN100,20,pcs,120.00,USD,2400.00,14\n" +
      "EPDM Sealing Rings,40,pcs,15.00,USD,600.00,7\n";

    const uploadRes = await request.post(`${API_BASE}/api/v1/quotations/${quoteId}/documents`, {
      headers: { "X-API-Key": DEV_API_KEY },
      multipart: {
        file: {
          name: "docker_quote.csv",
          mimeType: "text/csv",
          buffer: Buffer.from(csvContent, "utf-8"),
        },
      },
    });
    expect(uploadRes.status()).toBe(201);

    // 4. Trigger Extraction
    const extractRes = await request.post(`${API_BASE}/api/v1/quotations/${quoteId}/extract`, {
      headers,
    });
    expect(extractRes.status()).toBe(200);

    // Wait for extraction to complete
    let extractionCompleted = false;
    for (let i = 0; i < 20; i++) {
      const extCheck = await request.get(
        `${API_BASE}/api/v1/quotations/${quoteId}/extractions/latest`,
        { headers }
      );
      if (extCheck.status() === 200) {
        const extData = await extCheck.json();
        if (extData.line_items && extData.line_items.length >= 2) {
          extractionCompleted = true;
          break;
        }
      }
      await page.waitForTimeout(500);
    }
    expect(extractionCompleted).toBe(true);

    // 5. Navigate to the Live Frontend Review Workspace
    await page.goto(`/quotations/${quoteId}/review`);

    // Verify workspace layout & live quotation data
    await expect(page.getByText("Docker Test Industries Ltd").first()).toBeVisible();
    await expect(page.getByText("Ref: DOCKER-Q100")).toBeVisible();
    await expect(page.getByText("High Pressure Flange DN100").first()).toBeVisible();
    await expect(page.getByText("EPDM Sealing Rings").first()).toBeVisible();

    // Verify Document Viewer on the left
    await expect(page.getByLabel("Original Document Viewer")).toBeVisible();

    // 6. Evidence Navigation: Click line item to focus evidence
    const reviewRegion = page.getByRole("region", { name: "Extracted Structured Data and Verification" });
    const flangeRow = reviewRegion.getByText("High Pressure Flange DN100", { exact: true });
    await flangeRow.click();
    await expect(flangeRow).toBeVisible();

    // 7. Human Correction: Open edit modal and update price with audit reason
    const editButton = reviewRegion.getByRole("button", { name: "Edit line item" }).first();
    await editButton.click();

    await expect(page.getByText("Edit Line Item (Preserves Quoted vs Calculated)")).toBeVisible();
    await expect(page.getByText("Phase 3 Audit Safeguard:")).toBeVisible();

    // Enter audit reason
    const reasonInput = page.getByLabel("Reason for Change *");
    await reasonInput.fill("Verified invoice discount applied to DN100 unit price");

    // Save correction
    const saveButton = page.getByRole("button", { name: "Save Correction" });
    await saveButton.click();

    // Modal closes and item reflects corrected status
    await expect(page.getByText("Corrected").first()).toBeVisible({ timeout: 5000 });

    // 8. Approval Flow: Approve extraction quality
    const approveBtn = page.getByRole("button", { name: "Approve Extraction" });
    await approveBtn.click();

    // Extraction decision modal confirms semantics and validation
    await expect(page.getByText("Approve Extraction Quality")).toBeVisible();
    await expect(
      page.getByText("This action verifies extraction accuracy for downstream RFQ comparison.")
    ).toBeVisible();

    const confirmApproveBtn = page.getByRole("button", { name: "Confirm & Approve Extraction" });
    await confirmApproveBtn.click();

    // Review status pill updates to Extraction Approved
    await expect(page.getByText("Extraction Approved").first()).toBeVisible({ timeout: 5000 });

    // 9. Verify Immutable Audit Trail
    const auditBtn = page.getByRole("button", { name: /Audit Trail/ });
    await auditBtn.click();

    await expect(page.getByText(/Immutable Audit Trail/)).toBeVisible();
    await expect(page.getByText("Line Item Corrected")).toBeVisible();
    await expect(page.getByRole("dialog").getByText("Extraction Approved")).toBeVisible();
  });
});
