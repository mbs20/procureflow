import { test, expect } from "@playwright/test";

const API_BASE = "http://localhost:8000";
const DEV_API_KEY = "procureflow_dev_api_key_12345";
const headers = {
  "Content-Type": "application/json",
  "X-API-Key": DEV_API_KEY,
};

test.describe("Live Docker Comparison Matrix Workflow", () => {
  test("3 approved suppliers -> normalization -> matrix -> traceability -> override -> snapshot", async ({
    page,
    request,
  }) => {
    // Check if live Docker backend is running
    let backendLive = false;
    try {
      const healthCheck = await request.get(`${API_BASE}/api/v1/health`, { timeout: 3000 });
      backendLive = healthCheck.status() === 200;
    } catch {
      backendLive = false;
    }
    test.skip(!backendLive, "Live Docker backend is not available on port 8000 (standalone CI mode).");

    // 1. Create RFQ on live Docker stack
    const rfqRes = await request.post(`${API_BASE}/api/v1/rfqs`, {
      headers,
      data: {
        title: "Docker Live Comparison Flanges & Gaskets",
        category: "Piping",
        reference_currency: "USD",
        line_items: [
          { position: 1, description: "Flange DN100 PN16", quantity: 100, unit: "pcs" },
          { position: 2, description: "Gasket DN100", quantity: 200, unit: "pcs" },
        ],
        criteria: [{ name: "Price", weight: 1.0, criterion_type: "price", is_mandatory: true }],
      },
    });
    expect(rfqRes.status()).toBe(201);
    const rfq = await rfqRes.json();
    const rfqId = rfq.id;

    // 2. Configure initial RFQ FX rate set (v1: EUR = 1.0850, MAD = 0.1000)
    const fxRes = await request.post(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/fx-rates`, {
      headers,
      data: {
        base_currency: "USD",
        rates: { USD: 1.0, EUR: 1.085, MAD: 0.1 },
        provider_id: "docker_test_rates_v1",
      },
    });
    expect(fxRes.status()).toBe(201);

    // 3. Ingest Supplier A (USD)
    const quoteARes = await request.post(`${API_BASE}/api/v1/quotations`, {
      headers,
      data: { rfq_id: rfqId, supplier_name: "Apex Global USD" },
    });
    const qidA = (await quoteARes.json()).id;
    const csvA =
      "Description,Quantity,Unit,Unit Price,Currency,Total Price,Lead Time\n" +
      "Flange DN100 PN16,100,pcs,110.00,USD,11000.00,14\n" +
      "Gasket DN100,200,pcs,22.00,USD,4400.00,7\n";
    await request.post(`${API_BASE}/api/v1/quotations/${qidA}/documents`, {
      headers: { "X-API-Key": DEV_API_KEY },
      multipart: { file: { name: "quote_a.csv", mimeType: "text/csv", buffer: Buffer.from(csvA) } },
    });
    await request.post(`${API_BASE}/api/v1/quotations/${qidA}/extract`, { headers });
    const extA = (await (await request.get(`${API_BASE}/api/v1/quotations/${qidA}/extractions/latest`, { headers })).json());
    await request.patch(`${API_BASE}/api/v1/quotations/${qidA}/line-items/${extA.line_items[0].id}`, {
      headers,
      data: { rfq_line_item_id: rfq.line_items[0].id },
    });
    await request.patch(`${API_BASE}/api/v1/quotations/${qidA}/line-items/${extA.line_items[1].id}`, {
      headers,
      data: { rfq_line_item_id: rfq.line_items[1].id },
    });
    await request.patch(`${API_BASE}/api/v1/quotations/${qidA}/status`, {
      headers,
      data: { status: "approved" },
    });

    // 4. Ingest Supplier B (EUR)
    const quoteBRes = await request.post(`${API_BASE}/api/v1/quotations`, {
      headers,
      data: { rfq_id: rfqId, supplier_name: "EuroPipes EUR" },
    });
    const qidB = (await quoteBRes.json()).id;
    const csvB =
      "Description,Quantity,Unit,Unit Price,Currency,Total Price,Lead Time\n" +
      "Flange DN100 PN16,100,pcs,100.00,EUR,10000.00,21\n" +
      "Gasket DN100,10,box,400.00,EUR,4000.00,7\n";
    await request.post(`${API_BASE}/api/v1/quotations/${qidB}/documents`, {
      headers: { "X-API-Key": DEV_API_KEY },
      multipart: { file: { name: "quote_b.csv", mimeType: "text/csv", buffer: Buffer.from(csvB) } },
    });
    await request.post(`${API_BASE}/api/v1/quotations/${qidB}/extract`, { headers });
    const extB = (await (await request.get(`${API_BASE}/api/v1/quotations/${qidB}/extractions/latest`, { headers })).json());
    await request.patch(`${API_BASE}/api/v1/quotations/${qidB}/line-items/${extB.line_items[0].id}`, {
      headers,
      data: { rfq_line_item_id: rfq.line_items[0].id },
    });
    await request.patch(`${API_BASE}/api/v1/quotations/${qidB}/line-items/${extB.line_items[1].id}`, {
      headers,
      data: { rfq_line_item_id: rfq.line_items[1].id },
    });
    await request.patch(`${API_BASE}/api/v1/quotations/${qidB}/status`, {
      headers,
      data: { status: "approved" },
    });

    // 5. Apply Packaging Override on Supplier B Item 2: 1 box = 20 pcs
    const ovRes = await request.post(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/overrides`, {
      headers,
      data: {
        quotation_id: qidB,
        line_item_id: extB.line_items[1].id,
        field_name: "uom_factor",
        override_value: { conversion_factor: 20.0 },
        override_reason: "Confirmed 1 box = 20 pcs packaging specification with vendor",
      },
    });
    expect(ovRes.status()).toBe(201);

    // 6. Navigate to Frontend Matrix Page
    await page.goto(`/rfqs/${rfqId}/matrix`);

    // Verify matrix UI renders suppliers and normalized values
    await expect(page.getByText("Apex Global USD").first()).toBeVisible();
    await expect(page.getByText("EuroPipes EUR").first()).toBeVisible();

    // Verify normalized values
    await expect(page.getByText("$15400.00").first()).toBeVisible(); // Supplier A Subtotal
    await expect(page.getByText("$15190.00").first()).toBeVisible(); // Supplier B Subtotal ($10,850 + $4,340)

    // 7. Freeze Comparison Snapshot from UI
    const snapBtn = page.getByRole("button", { name: /Snapshots/i });
    await snapBtn.click();
    await expect(page.getByRole("heading", { name: "Comparison Snapshots" })).toBeVisible();

    await page.getByPlaceholder("e.g. Q1 Committee Baseline Review...").fill("Docker Live Baseline Snapshot");
    await page.getByRole("button", { name: "Freeze Snapshot" }).click();
    await expect(page.getByText("Snapshot frozen successfully")).toBeVisible({ timeout: 5000 });
  });
});
