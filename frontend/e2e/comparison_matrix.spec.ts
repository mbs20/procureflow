import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const MOCK_RFQ_ID = "11111111-2222-3333-4444-555555555555";

const mockMatrixData = {
  rfq_id: MOCK_RFQ_ID,
  rfq_title: "Industrial Piping & Flange Procurement Q4",
  reference_currency: "USD",
  normalization_engine_version: "v4.0.0",
  active_overrides_count: 1,
  snapshots_count: 1,
  warnings_summary: [],
  computed_at: new Date().toISOString(),
  fx_rate_set: {
    id: "fx-set-001",
    rfq_id: MOCK_RFQ_ID,
    version: 1,
    base_currency: "USD",
    rates: {
      USD: 1.0,
      EUR: 1.08,
      MAD: 0.1,
    },
    effective_date: "2026-09-07",
    provider_id: "static_seed",
    is_synthetic: true,
    is_current: true,
    created_by: "system_seed",
    created_at: new Date().toISOString(),
  },
  suppliers: [
    {
      quotation_id: "q-001",
      supplier_name: "Apex Global Industrial Ltd",
      supplier_reference: "APEX-2026-09",
      status: "approved",
      extraction_version: "1.0",
      original_currency: "USD",
      rfq_coverage_pct: 100.0,
      quoted_items_count: 2,
      total_rfq_items: 2,
      quoted_grand_total: 15400.0,
      normalized_line_item_subtotal: 15400.0,
      normalized_comparable_total: 15400.0,
      has_unknown_commercial_components: false,
      payment_terms_original: "Net 30 days",
      payment_terms_normalized: "NET_30 (Standard Commercial Credit)",
      payment_terms_code: "NET_30",
      overall_lead_time_original: "14 calendar days",
      overall_lead_time_normalized: "14 calendar days",
      overall_lead_time_days: 14,
      unresolved_count: 0,
      warnings_count: 0,
      warnings: [],
    },
    {
      quotation_id: "q-002",
      supplier_name: "EuroPipes & Valves GmbH",
      supplier_reference: "EPV-8831",
      status: "approved",
      extraction_version: "1.0",
      original_currency: "EUR",
      rfq_coverage_pct: 100.0,
      quoted_items_count: 2,
      total_rfq_items: 2,
      quoted_grand_total: 14000.0,
      normalized_line_item_subtotal: 15120.0,
      normalized_comparable_total: 15120.0,
      has_unknown_commercial_components: false,
      payment_terms_original: "Net 30",
      payment_terms_normalized: "NET_30 (Standard Commercial Credit)",
      payment_terms_code: "NET_30",
      overall_lead_time_original: "2-3 weeks",
      overall_lead_time_normalized: "21 calendar days (conservative range upper bound)",
      overall_lead_time_days: 21,
      unresolved_count: 0,
      warnings_count: 0,
      warnings: [],
    },
    {
      quotation_id: "q-003",
      supplier_name: "Maghreb Tubes & Raccords SARL",
      supplier_reference: "MTR-2026-004",
      status: "approved",
      extraction_version: "1.0",
      original_currency: "MAD",
      rfq_coverage_pct: 50.0,
      quoted_items_count: 1,
      total_rfq_items: 2,
      quoted_grand_total: 120000.0,
      normalized_line_item_subtotal: 12000.0,
      normalized_comparable_total: null,
      has_unknown_commercial_components: false,
      payment_terms_original: "30% advance, 70% before delivery",
      payment_terms_normalized: "ADVANCE_PARTIAL (Staged Milestone Payment)",
      payment_terms_code: "ADVANCE_PARTIAL",
      overall_lead_time_original: "10 business days",
      overall_lead_time_normalized: "10 business days (preserved calendar distinct)",
      overall_lead_time_days: 10,
      unresolved_count: 0,
      warnings_count: 1,
      warnings: ["Missing 1 required RFQ line item"],
    },
  ],
  required_line_items: [
    {
      rfq_line_item_id: "rfq-item-1",
      position: 1,
      description: "Stainless Steel Flange DN100 PN16",
      required_quantity: 100.0,
      required_unit: "pcs",
      supplier_cells: {
        "q-001": {
          is_quoted: true,
          line_item_id: "item-1-1",
          quoted_description: "Stainless Steel Flange DN100 PN16",
          quoted_quantity: 100.0,
          quoted_unit: "pcs",
          quoted_unit_price: 110.0,
          quoted_total_price: 11000.0,
          calculated_total_price: 11000.0,
          has_math_discrepancy: false,
          original_currency: "USD",
          canonical_quantity: 100.0,
          canonical_unit: "pcs",
          uom_conversion_factor: 1.0,
          uom_status: "normalized",
          fx_rate_used: 1.0,
          fx_status: "normalized",
          normalized_unit_price: 110.0,
          normalized_extended_price: 11000.0,
          line_lead_time_days: 14,
          line_lead_time_display: "14 calendar days",
          line_lead_time_type: "CALENDAR_DAYS",
          overall_cell_status: "normalized",
          is_human_overridden: false,
          warnings: [],
          source_page: 1,
          source_evidence: {
            page_number: 1,
            bounding_box: { x: 50, y: 120, width: 500, height: 20 },
            raw_text: "Flange DN100 PN16 - 100 pcs @ 110 USD",
          },
        },
        "q-002": {
          is_quoted: true,
          line_item_id: "item-2-1",
          quoted_description: "Edelstahl-Flansch DN100 PN16",
          quoted_quantity: 100.0,
          quoted_unit: "pcs",
          quoted_unit_price: 100.0,
          quoted_total_price: 10000.0,
          calculated_total_price: 10000.0,
          has_math_discrepancy: false,
          original_currency: "EUR",
          canonical_quantity: 100.0,
          canonical_unit: "pcs",
          uom_conversion_factor: 1.0,
          uom_status: "normalized",
          fx_rate_used: 1.08,
          fx_status: "normalized",
          normalized_unit_price: 108.0,
          normalized_extended_price: 10800.0,
          line_lead_time_days: 21,
          line_lead_time_display: "2-3 weeks (21 days upper bound)",
          line_lead_time_type: "RANGE_WEEKS",
          overall_cell_status: "normalized",
          is_human_overridden: false,
          warnings: [],
          source_page: 1,
          source_evidence: {
            page_number: 1,
            bounding_box: { x: 45, y: 150, width: 510, height: 22 },
            raw_text: "Edelstahl-Flansch DN100 PN16 - 100 pcs @ 100 EUR",
          },
        },
        "q-003": {
          is_quoted: true,
          line_item_id: "item-3-1",
          quoted_description: "Bride Inox DN100 PN16",
          quoted_quantity: 100.0,
          quoted_unit: "pcs",
          quoted_unit_price: 1200.0,
          quoted_total_price: 120000.0,
          calculated_total_price: 120000.0,
          has_math_discrepancy: false,
          original_currency: "MAD",
          canonical_quantity: 100.0,
          canonical_unit: "pcs",
          uom_conversion_factor: 1.0,
          uom_status: "normalized",
          fx_rate_used: 0.1,
          fx_status: "normalized",
          normalized_unit_price: 120.0,
          normalized_extended_price: 12000.0,
          line_lead_time_days: 10,
          line_lead_time_display: "10 business days",
          line_lead_time_type: "BUSINESS_DAYS",
          overall_cell_status: "normalized",
          is_human_overridden: false,
          warnings: [],
          source_page: 1,
          source_evidence: {
            page_number: 1,
            bounding_box: { x: 40, y: 110, width: 480, height: 18 },
            raw_text: "Bride Inox DN100 PN16 - 100 pcs @ 1200 MAD",
          },
        },
      },
    },
    {
      rfq_line_item_id: "rfq-item-2",
      position: 2,
      description: "EPDM Sealing Gasket DN100",
      required_quantity: 200.0,
      required_unit: "pcs",
      supplier_cells: {
        "q-001": {
          is_quoted: true,
          line_item_id: "item-1-2",
          quoted_description: "EPDM Sealing Gasket DN100",
          quoted_quantity: 200.0,
          quoted_unit: "pcs",
          quoted_unit_price: 22.0,
          quoted_total_price: 4400.0,
          calculated_total_price: 4400.0,
          has_math_discrepancy: false,
          original_currency: "USD",
          canonical_quantity: 200.0,
          canonical_unit: "pcs",
          uom_conversion_factor: 1.0,
          uom_status: "normalized",
          fx_rate_used: 1.0,
          fx_status: "normalized",
          normalized_unit_price: 22.0,
          normalized_extended_price: 4400.0,
          line_lead_time_days: 7,
          line_lead_time_display: "7 days",
          line_lead_time_type: "CALENDAR_DAYS",
          overall_cell_status: "normalized",
          is_human_overridden: false,
          warnings: [],
          source_page: 1,
          source_evidence: {
            page_number: 1,
            bounding_box: { x: 50, y: 160, width: 500, height: 20 },
            raw_text: "EPDM Sealing Gasket DN100 - 200 pcs @ 22 USD",
          },
        },
        "q-002": {
          is_quoted: true,
          line_item_id: "item-2-2",
          quoted_description: "EPDM Dichtung DN100 (Box of 20)",
          quoted_quantity: 10.0,
          quoted_unit: "box",
          quoted_unit_price: 400.0,
          quoted_total_price: 4000.0,
          calculated_total_price: 4000.0,
          has_math_discrepancy: false,
          original_currency: "EUR",
          canonical_quantity: 200.0,
          canonical_unit: "pcs",
          uom_conversion_factor: 20.0,
          uom_status: "normalized",
          fx_rate_used: 1.08,
          fx_status: "normalized",
          normalized_unit_price: 21.6,
          normalized_extended_price: 4320.0,
          line_lead_time_days: 7,
          line_lead_time_display: "1 week",
          line_lead_time_type: "WEEKS",
          overall_cell_status: "normalized",
          is_human_overridden: true,
          override_id: "ovr-001",
          override_reason: "Confirmed packaging specification: 1 box = 20 pcs",
          warnings: [],
          source_page: 1,
          source_evidence: {
            page_number: 1,
            bounding_box: { x: 45, y: 190, width: 510, height: 22 },
            raw_text: "EPDM Dichtung DN100 (Box of 20) - 10 box @ 400 EUR",
          },
        },
        "q-003": {
          is_quoted: false,
          overall_cell_status: "unresolved",
          warnings: ["Line item not quoted by supplier"],
        },
      },
    },
  ],
  extra_line_items: [],
};

const mockRFQsList = [
  {
    id: MOCK_RFQ_ID,
    title: "Industrial Piping & Flange Procurement Q4",
    category: "industrial_equipment",
    status: "active",
    reference_currency: "USD",
  },
];

const mockSnapshotsList = [
  {
    id: "snap-001",
    rfq_id: MOCK_RFQ_ID,
    snapshot_version: 1,
    title: "Initial Baseline Comparison",
    reference_currency: "USD",
    fx_rate_set_id: "fx-set-001",
    normalization_engine_version: "v4.0.0",
    created_by: "procurement_analyst",
    created_at: new Date().toISOString(),
    matrix_data: {},
  },
];

test.describe("Supplier Comparison Matrix Workflow (Phase 4)", () => {
  test.beforeEach(async ({ page }) => {
    await page.route(/\/api\/v1\/rfqs(\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: mockRFQsList,
          total: mockRFQsList.length,
          page: 1,
          page_size: 50,
          total_pages: 1,
        }),
      });
    });

    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/matrix$`), async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockMatrixData),
      });
    });

    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/matrix/snapshots`), async (route) => {
      if (route.request().method() === "POST") {
        const postBody = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: "snap-002",
            rfq_id: MOCK_RFQ_ID,
            snapshot_version: 2,
            title: postBody.title || "Post-Audit Final Matrix",
            reference_currency: "USD",
            fx_rate_set_id: "fx-set-001",
            normalization_engine_version: "v4.0.0",
            created_by: "system_user",
            created_at: new Date().toISOString(),
            matrix_data: {},
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockSnapshotsList),
        });
      }
    });

    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/matrix/fx-rates`), async (route) => {
      if (route.request().method() === "POST") {
        const postData = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: "fx-set-002",
            rfq_id: MOCK_RFQ_ID,
            version: 2,
            base_currency: "USD",
            rates: postData.rates,
            effective_date: postData.effective_date,
            provider_id: postData.provider_id || "custom",
            is_synthetic: false,
            is_current: true,
            created_by: "user",
            created_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([mockMatrixData.fx_rate_set]),
        });
      }
    });

    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/matrix/overrides`), async (route) => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "ovr-new",
          rfq_id: MOCK_RFQ_ID,
          quotation_id: "q-002",
          line_item_id: "item-2-2",
          field_name: "uom_conversion_factor",
          original_value: {},
          override_value: { conversion_factor: 20.0 },
          override_reason: "Confirmed packaging specification with vendor",
          actor_id: "user",
          created_at: new Date().toISOString(),
          is_active: true,
        }),
      });
    });
  });

  test("loads matrix, shows multi-supplier normalization, dual prices, and accessibility check", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/matrix`);

    // Verify Main Heading and Subheading
    await expect(page.getByRole("heading", { name: "Normalized Comparison Matrix" })).toBeVisible();
    await expect(
      page.getByText("Apples-to-apples commercial & technical comparison with strict data provenance.")
    ).toBeVisible();

    // Verify 3 Suppliers Present in Headers
    await expect(page.getByText("Apex Global Industrial Ltd").first()).toBeVisible();
    await expect(page.getByText("EuroPipes & Valves GmbH").first()).toBeVisible();
    await expect(page.getByText("Maghreb Tubes & Raccords SARL").first()).toBeVisible();

    // Verify Normalized Line-Item Subtotal Row
    await expect(page.getByText("Normalized Line-Item Subtotal").first()).toBeVisible();

    // Verify Maghreb Tubes coverage
    await expect(page.getByText("50% (1/2)")).toBeVisible();

    // Verify Missing RFQ Item Indicator
    await expect(page.getByText("NOT QUOTED", { exact: true })).toBeVisible();
    await expect(page.getByText("Withheld (Incomplete scope)")).toBeVisible();

    // Run Axe Accessibility Scan
    const accessibilityScanResults = await new AxeBuilder({ page })
      .disableRules(["color-contrast"])
      .analyze();
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test("inspects Cell Traceability Drawer with math audit and source evidence", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/matrix`);

    // Click on the EuroPipes Line Item 1 cell ($108.0000)
    const euroCell = page.getByText("$108.0000");
    await euroCell.click();

    // Verify Traceability Drawer is open
    await expect(page.getByRole("heading", { name: "Cell Traceability & Provenance" })).toBeVisible();
    await expect(page.getByText("EuroPipes & Valves GmbH • #1 Stainless Steel Flange DN100 PN16")).toBeVisible();

    // Verify Tabs & Provenance Details
    await expect(page.getByText("Evidence & Normalization")).toBeVisible();
    await expect(page.getByText("Normalized Comparable")).toBeVisible();
    await expect(page.getByText("Quoted Original", { exact: true })).toBeVisible();

    // Close Drawer
    const closeBtn = page.getByRole("button").filter({ has: page.locator("svg.lucide-x") }).first();
    await closeBtn.click();
    await expect(page.getByRole("heading", { name: "Cell Traceability & Provenance" })).not.toBeVisible();
  });

  test("manages FX Rate Sets and freezes Comparison Snapshots", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/matrix`);

    // 1. Open FX Rates Modal
    const fxBtn = page.getByRole("button", { name: /FX Rates \(v1\)/i });
    await fxBtn.click();

    await expect(page.getByRole("heading", { name: "Configure RFQ Exchange Rates" })).toBeVisible();
    await expect(page.getByText("Synthetic Test Rates Active:")).toBeVisible();

    // Close FX modal
    const closeFXBtn = page.getByRole("button").filter({ has: page.locator("svg.lucide-x") }).first();
    await closeFXBtn.click();
    await expect(page.getByRole("heading", { name: "Configure RFQ Exchange Rates" })).not.toBeVisible();

    // 2. Open Snapshots Modal
    const snapBtn = page.getByRole("button", { name: /Snapshots \(1\)/i });
    await snapBtn.click();

    await expect(page.getByRole("heading", { name: "Comparison Snapshots" })).toBeVisible();
    await expect(page.getByText("Initial Baseline Comparison")).toBeVisible();

    // Freeze new snapshot
    await page.getByPlaceholder("e.g. Q1 Committee Baseline Review...").fill("Post-Audit Final Matrix");

    const freezeBtn = page.getByRole("button", { name: "Freeze Snapshot" });
    await freezeBtn.click();

    // Verify snapshot success message
    await expect(page.getByText("Snapshot frozen successfully")).toBeVisible({ timeout: 5000 });
  });
});
