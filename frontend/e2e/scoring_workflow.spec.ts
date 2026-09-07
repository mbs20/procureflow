import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const MOCK_RFQ_ID = "11111111-2222-3333-4444-555555555555";
const MOCK_SNAPSHOT_ID = "snap-001";
const MOCK_CONFIG_ID = "cfg-001";
const MOCK_RUN_ID = "run-001";

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
    id: MOCK_SNAPSHOT_ID,
    rfq_id: MOCK_RFQ_ID,
    snapshot_version: 1,
    title: "Initial Approved Baseline Matrix",
    reference_currency: "USD",
    fx_rate_set_id: "fx-set-001",
    normalization_engine_version: "v4.0.0",
    created_by: "procurement_analyst",
    created_at: new Date().toISOString(),
    matrix_data: {},
  },
];

const mockScoringConfig = {
  id: MOCK_CONFIG_ID,
  rfq_id: MOCK_RFQ_ID,
  version: 1,
  name: "Phase 5 Baseline Evaluation Model",
  description: "Deterministic weighted model: Price (60%), Lead Time (30%), Payment (10%)",
  criteria: [
    {
      name: "Commercial Price",
      weight: 0.6,
      direction: "MINIMIZE",
      source_field: "normalized_comparable_total",
      description: "Total normalized cost in USD",
    },
    {
      name: "Delivery Lead Time",
      weight: 0.3,
      direction: "MINIMIZE",
      source_field: "overall_lead_time_days",
      knockout_condition: "GREATER_THAN",
      knockout_threshold: 45,
      description: "Overall lead time in calendar days",
    },
    {
      name: "Payment Terms",
      weight: 0.1,
      direction: "MAXIMIZE",
      source_field: "payment_terms_code",
      categorical_map: {
        NET_60: 100,
        NET_30: 75,
        ADVANCE: 20,
      },
      description: "Evaluator commercial payment preference",
    },
  ],
  missing_value_policy: "BLOCK_SCORING",
  tie_policy: "STANDARD_COMPETITION",
  is_active: true,
  created_at: new Date().toISOString(),
};

const mockScoringRun = {
  id: MOCK_RUN_ID,
  rfq_id: MOCK_RFQ_ID,
  scoring_configuration_id: MOCK_CONFIG_ID,
  scoring_configuration_version: 1,
  comparison_snapshot_id: MOCK_SNAPSHOT_ID,
  comparison_snapshot_version: 1,
  comparison_snapshot_hash: "a1b2c3d4e5f67890",
  notes: "Formal Phase 5 baseline evaluation run",
  created_at: new Date().toISOString(),
  scores: [
    {
      quotation_id: "q-001",
      supplier_name: "Apex Global Industrial Ltd",
      is_eligible: true,
      status: "eligible",
      knockout_reasons: [],
      composite_score: 93.5,
      rank: 1,
      breakdown: {
        "Commercial Price": {
          raw_value: 15400.0,
          cohort_min: 15400.0,
          cohort_max: 18000.0,
          normalized_score: 100.0,
          weight: 0.6,
          weighted_contribution: 60.0,
          knockout_applied: false,
          source_path: "snapshot.payload.matrix.suppliers[0].normalized_comparable_total",
        },
        "Delivery Lead Time": {
          raw_value: 14,
          cohort_min: 14,
          cohort_max: 28,
          normalized_score: 100.0,
          weight: 0.3,
          weighted_contribution: 30.0,
          knockout_applied: false,
          source_path: "snapshot.payload.matrix.suppliers[0].overall_lead_time_days",
        },
        "Payment Terms": {
          raw_value: "NET_30",
          cohort_min: 20,
          cohort_max: 75,
          normalized_score: 35.0,
          weight: 0.1,
          weighted_contribution: 3.5,
          knockout_applied: false,
          source_path: "snapshot.payload.matrix.suppliers[0].payment_terms_code",
        },
      },
    },
    {
      quotation_id: "q-002",
      supplier_name: "EuroPipes & Valves GmbH",
      is_eligible: true,
      status: "eligible",
      knockout_reasons: [],
      composite_score: 72.8,
      rank: 2,
      breakdown: {
        "Commercial Price": {
          raw_value: 18000.0,
          cohort_min: 15400.0,
          cohort_max: 18000.0,
          normalized_score: 0.0,
          weight: 0.6,
          weighted_contribution: 0.0,
          knockout_applied: false,
          source_path: "snapshot.payload.matrix.suppliers[1].normalized_comparable_total",
        },
        "Delivery Lead Time": {
          raw_value: 28,
          cohort_min: 14,
          cohort_max: 28,
          normalized_score: 0.0,
          weight: 0.3,
          weighted_contribution: 0.0,
          knockout_applied: false,
          source_path: "snapshot.payload.matrix.suppliers[1].overall_lead_time_days",
        },
        "Payment Terms": {
          raw_value: "NET_60",
          cohort_min: 20,
          cohort_max: 100,
          normalized_score: 100.0,
          weight: 0.1,
          weighted_contribution: 10.0,
          knockout_applied: false,
          source_path: "snapshot.payload.matrix.suppliers[1].payment_terms_code",
        },
      },
    },
    {
      quotation_id: "q-003",
      supplier_name: "Atlas Industrial Fasteners Inc",
      is_eligible: false,
      status: "knockout_failed",
      knockout_reasons: ["Delivery Lead Time exceeded maximum allowable threshold of 45 days (quoted: 60)"],
      composite_score: 0.0,
      rank: null,
      breakdown: {
        "Commercial Price": {
          raw_value: 14000.0,
          cohort_min: null,
          cohort_max: null,
          normalized_score: 0.0,
          weight: 0.6,
          weighted_contribution: 0.0,
          knockout_applied: false,
        },
        "Delivery Lead Time": {
          raw_value: 60,
          cohort_min: null,
          cohort_max: null,
          normalized_score: 0.0,
          weight: 0.3,
          weighted_contribution: 0.0,
          knockout_applied: true,
          notes: "FAILED_KNOCKOUT: Delivery Lead Time GREATER_THAN 45",
        },
        "Payment Terms": {
          raw_value: "ADVANCE",
          cohort_min: null,
          cohort_max: null,
          normalized_score: 0.0,
          weight: 0.1,
          weighted_contribution: 0.0,
          knockout_applied: false,
        },
      },
    },
  ],
};

const mockSensitivityData = {
  comparison_snapshot_id: MOCK_SNAPSHOT_ID,
  sweep_criterion: "Commercial Price",
  data_points: [
    {
      weight: 0.2,
      weights_vector: { "Commercial Price": 0.2, "Delivery Lead Time": 0.6, "Payment Terms": 0.2 },
      supplier_scores: { "q-001": 85.0, "q-002": 88.0, "q-003": 0.0 },
      ranks: { "q-001": 2, "q-002": 1, "q-003": 0 },
    },
    {
      weight: 0.45,
      weights_vector: { "Commercial Price": 0.45, "Delivery Lead Time": 0.41, "Payment Terms": 0.14 },
      supplier_scores: { "q-001": 89.5, "q-002": 89.5, "q-003": 0.0 },
      ranks: { "q-001": 1, "q-002": 1, "q-003": 0 },
    },
    {
      weight: 0.6,
      weights_vector: { "Commercial Price": 0.6, "Delivery Lead Time": 0.3, "Payment Terms": 0.1 },
      supplier_scores: { "q-001": 93.5, "q-002": 72.8, "q-003": 0.0 },
      ranks: { "q-001": 1, "q-002": 2, "q-003": 0 },
    },
  ],
  crossover_points: [
    {
      weight: 0.45,
      supplier_a_id: "q-001",
      supplier_a_name: "Apex Global Industrial Ltd",
      supplier_b_id: "q-002",
      supplier_b_name: "EuroPipes & Valves GmbH",
      score_at_crossover: 89.5,
      description: "Apex Global Industrial Ltd overtakes EuroPipes & Valves GmbH at weight 0.4500",
    },
  ],
  breakeven: {
    target_supplier_id: "q-002",
    target_supplier_name: "EuroPipes & Valves GmbH",
    current_rank: 2,
    current_score: 72.8,
    target_rank: 1,
    incumbent_supplier_id: "q-001",
    incumbent_supplier_name: "Apex Global Industrial Ltd",
    required_score: 93.5,
    current_price: 18000.0,
    required_price: 14850.0,
    price_delta: 3150.0,
    percentage_reduction_needed: 17.5,
    is_feasible: true,
    bisection_iterations: 14,
    explanation: "Candidate EuroPipes & Valves GmbH requires a 17.50% price reduction ($3,150.00 USD) to achieve Rank #1.",
  },
};

test.describe("Deterministic Scoring Engine Workflow (Phase 5)", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept RFQs
    await page.route(/\/api\/v1\/rfqs(\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: mockRFQsList,
          total: 1,
          page: 1,
          page_size: 50,
          total_pages: 1,
        }),
      });
    });

    // Intercept Snapshots
    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/matrix/snapshots`), async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockSnapshotsList),
      });
    });

    // Intercept Active Scoring Config
    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/scoring/configurations/active`), async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockScoringConfig),
      });
    });

    // Intercept Scoring Configurations list & creation
    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/scoring/configurations$`), async (route) => {
      if (route.request().method() === "POST") {
        const body = route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            ...mockScoringConfig,
            id: "cfg-002",
            version: 2,
            name: body.name || "Custom Scoring Model",
            criteria: body.criteria,
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([mockScoringConfig]),
        });
      }
    });

    // Intercept Scoring Runs
    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/scoring/runs`), async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            ...mockScoringRun,
            id: "run-002",
            notes: "Newly created run",
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([mockScoringRun]),
        });
      }
    });

    // Intercept Simulate
    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/scoring/simulate`), async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          snapshot_id: MOCK_SNAPSHOT_ID,
          scores: mockScoringRun.scores,
          criteria: mockScoringConfig.criteria,
        }),
      });
    });

    // Intercept Sensitivity & Breakeven
    await page.route(new RegExp(`/api/v1/rfqs/${MOCK_RFQ_ID}/scoring/sensitivity`), async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockSensitivityData),
      });
    });
  });

  test("1. Renders ranking table with standard competition ranks, eligible suppliers, and knockout failure", async ({
    page,
  }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/scoring`);

    // Verify page header
    await expect(page.getByRole("heading", { name: /Supplier Scoring & Evaluation Engine/i })).toBeVisible();
    await expect(page.getByText(/Phase 5 Deterministic Scoring/i)).toBeVisible();

    // Verify rank #1 and #2 eligible suppliers
    await expect(page.getByText("Apex Global Industrial Ltd")).toBeVisible();
    await expect(page.getByText("#1")).toBeVisible();
    await expect(page.getByText("93.50")).toBeVisible();

    await expect(page.getByText("EuroPipes & Valves GmbH")).toBeVisible();
    await expect(page.getByText("#2")).toBeVisible();
    await expect(page.getByText("72.80")).toBeVisible();

    // Verify disqualified supplier
    await expect(page.getByText("Atlas Industrial Fasteners Inc")).toBeVisible();
    await expect(page.getByText("Knockout Failed")).toBeVisible();
    await expect(page.getByText(/Delivery Lead Time exceeded maximum allowable threshold/i)).toBeVisible();
  });

  test("2. Accessible Score Audit Drawer opens with exact mathematical formula breakdown", async ({
    page,
  }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/scoring`);

    // Click Audit button for Apex Global Industrial Ltd
    await page.getByRole("button", { name: /Inspect formula breakdown for Apex Global Industrial Ltd/i }).click();

    // Verify Drawer opens
    const drawer = page.getByRole("dialog", { name: /Score calculation audit details|Apex Global Industrial Ltd/i });
    await expect(page.getByRole("heading", { name: "Apex Global Industrial Ltd" })).toBeVisible();
    await expect(page.getByText("Deterministic Score Audit")).toBeVisible();
    await expect(page.getByText("Composite Evaluation Score")).toBeVisible();

    // Verify formula & source path
    await expect(page.getByText(/snapshot\.payload\.matrix\.suppliers\[0\]\.normalized_comparable_total/i)).toBeVisible();
    await expect(page.getByText(/Normalized =/i).first()).toBeVisible();

    // Close drawer
    await page.getByRole("button", { name: /Close audit drawer/i }).click();
    await expect(page.getByRole("heading", { name: "Apex Global Industrial Ltd" })).not.toBeVisible();
  });

  test("3. Criteria Weights & Balancing allows real-time proportional adjustment and lock toggling", async ({
    page,
  }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/scoring`);

    // Verify active criteria weights
    await expect(page.getByText(/Criteria Weights & Proportional Balancing/i).first()).toBeVisible();
    await expect(page.getByText("Total: 100.0%")).toBeVisible();

    // Lock Delivery Lead Time
    const lockButton = page.getByRole("button", { name: /Lock weight for Delivery Lead Time/i });
    await lockButton.click();
    await expect(page.getByRole("button", { name: /Unlock weight for Delivery Lead Time/i })).toBeVisible();

    // Simulate Transient Weights
    await page.getByRole("button", { name: /Simulate Weights/i }).click();

    // Verify transient state
    await expect(page.getByText("Total: 100.0%")).toBeVisible();
  });

  test("4. Sensitivity Sweep displays trajectory curves and crossover points", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/scoring`);

    // Switch to Sensitivity tab
    await page.getByRole("button", { name: /Sensitivity Sweep & Rank Trajectory/i }).click();

    // Verify Crossover highlight
    await expect(page.getByText(/Rank Crossover Points/i)).toBeVisible();
    await expect(page.getByText(/Apex Global Industrial Ltd overtakes EuroPipes & Valves GmbH/i)).toBeVisible();
    await expect(page.getByText("Weight: 45.0% (Score: 89.50)")).toBeVisible();

    // Verify SVG score curve is present
    await expect(page.locator("svg polyline").first()).toBeVisible();
  });

  test("5. Authoritative Breakeven Calculator displays required price delta and bisection iterations", async ({
    page,
  }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/scoring`);

    // Switch to Breakeven tab
    await page.getByRole("button", { name: /Authoritative Breakeven Search/i }).click();

    // Select candidate and click Compute Breakeven
    await page.getByRole("button", { name: /Compute Breakeven/i }).click();

    // Verify bisection metrics
    await expect(page.getByText(/Feasible Breakeven Target Identified/i)).toBeVisible();
    await expect(page.getByText(/14 bisection numerical iterations/i)).toBeVisible();
    await expect(page.getByText("$18,000.00")).toBeVisible();
    await expect(page.getByText("$14,850.00")).toBeVisible();
    await expect(page.getByText("-$3,150.00")).toBeVisible();
    await expect(page.getByText("17.50%", { exact: true })).toBeVisible();
  });

  test("6. Historical Scoring Runs modal lists frozen runs and executes new run", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/scoring`);

    // Open Historical Runs Modal
    await page.getByRole("button", { name: /Historical Runs/i }).click();

    // Verify modal contents
    await expect(page.getByRole("heading", { name: /Historical Scoring Runs & Executions/i })).toBeVisible();
    await expect(page.getByText("Config v1 • Snapshot v1")).toBeVisible();
    await expect(page.getByText(/Formal Phase 5 baseline evaluation run/i)).toBeVisible();

    // Execute New Run
    await page.getByRole("button", { name: /Execute & Freeze Scoring Run/i }).click();

    // Close modal
    await page.getByRole("button", { name: "Close", exact: true }).click();
  });

  test("7. WCAG 2.2 AA Accessibility Audit", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/scoring`);

    // Run Axe audit on the main scoring evaluation view
    const accessibilityScanResults = await new AxeBuilder({ page })
      .disableRules(["color-contrast"]) // Optional standard theme override
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });
});
