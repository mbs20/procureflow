import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const MOCK_RFQ_ID = "11111111-2222-3333-4444-555555555555";
const MOCK_RUN_ID = "run-001";
const MOCK_NARRATIVE_ID = "narr-001";
const MOCK_AWARD_ID = "award-001";

const mockRFQsList = [
  {
    id: MOCK_RFQ_ID,
    title: "High-Load Bearings & Seals Procurement",
    category: "Mechanical",
    status: "evaluating",
    reference_currency: "USD",
  },
];

const mockRFQDetail = {
  id: MOCK_RFQ_ID,
  title: "High-Load Bearings & Seals Procurement",
  description: "Phase 6 evaluation and human award",
  category: "Mechanical",
  status: "evaluating",
  reference_currency: "USD",
  created_by: "buyer_admin",
  is_archived: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  line_items: [],
  criteria: [],
};

const mockScoringRuns = [
  {
    id: MOCK_RUN_ID,
    rfq_id: MOCK_RFQ_ID,
    run_number: 1,
    name: "Production Evaluation Model v1",
    comparison_snapshot_id: "snap-001",
    provenance_hash: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
    created_at: new Date().toISOString(),
    scores: [],
    results_payload: {
      suppliers: [
        {
          quotation_id: "supp-alpha",
          supplier_name: "Supplier Alpha",
          rank: 1,
          total_score: "88.5000",
          exact_total_score: "88.5000000000",
          eligibility_status: "eligible",
        },
        {
          quotation_id: "supp-beta",
          supplier_name: "Supplier Beta",
          rank: 2,
          total_score: "74.2000",
          exact_total_score: "74.2000000000",
          eligibility_status: "eligible",
        },
      ],
    },
  },
];

const mockNarrative: any = {
  id: MOCK_NARRATIVE_ID,
  rfq_id: MOCK_RFQ_ID,
  decision_context_id: "ctx-001",
  narrative_type: "decision_support_memo",
  generation_number: 1,
  origin: "ai_generated",
  current_origin: "ai_generated",
  provider: "mock",
  model_identifier: "mock-deterministic-v1",
  prompt_template_version: "1.0",
  prompt_template_hash: "hash123",
  rendered_prompt_hash: "hash456",
  response_schema_version: "1.0",
  generation_parameters: {},
  output_hash: "out123",
  is_superseded: false,
  generated_at: new Date().toISOString(),
  created_by: "procureflow_dev_api_key_12345",
  raw_structured_output: {
    executive_summary: "Supplier Alpha is the highest-ranked vendor with an overall score of 88.5000.",
    ranking_explanation: "Standard competitive ranking based on Price and Lead Time weighting.",
    per_supplier_analysis: [
      {
        supplier_id: "supp-alpha",
        supplier_name: "Supplier Alpha",
        rank: 1,
        total_score: "88.5000",
        strengths: ["Price: normalized 100/100"],
        weaknesses: [],
        score_context: "Ranked #1 with total score 88.5000",
      },
      {
        supplier_id: "supp-beta",
        supplier_name: "Supplier Beta",
        rank: 2,
        total_score: "74.2000",
        strengths: ["Lead Time: normalized 95/100"],
        weaknesses: ["Price: normalized 60/100"],
        score_context: "Ranked #2 with total score 74.2000",
      },
    ],
    trade_offs: "Supplier Alpha provides lower cost; Supplier Beta provides faster delivery.",
    decision_considerations: "Evaluate warranty terms before human award.",
    risk_factors: ["Minor price sensitivity observed."],
    data_limitations: ["Based solely on structured quotations."],
  },
  grounding_validation_result: {
    total_claims: 2,
    verified: 2,
    unsupported: 0,
    unverifiable: 0,
    details: [],
  },
  claims: [
    {
      id: "claim-1",
      claim_index: 0,
      text: "Supplier Alpha achieved a total score of 88.5000 and is ranked #1.",
      claim_type: "deterministic_fact",
      grounding_status: "verified",
      referenced_supplier_ids: ["supp-alpha"],
      referenced_criterion_ids: [],
      referenced_evidence_ids: [],
      fact_references: [
        {
          reference_type: "supplier_score",
          supplier_id: "supp-alpha",
          authoritative_value: "88.5000",
        },
      ],
    },
  ],
  revisions: [],
};

test.describe("Phase 6: Evidence-Backed Decisions & Human Award Workflow", () => {
  test.beforeEach(async ({ page }) => {
    mockNarrative.revisions = [];
    mockNarrative.current_origin = "ai_generated";

    // 1. Scoring runs
    await page.route(/\/api\/v1\/rfqs\/[^/]+\/scoring\/runs/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockScoringRuns),
      });
    });

    // 2. Decision narratives (generate & list)
    await page.route(/\/api\/v1\/rfqs\/[^/]+\/decisions\/narratives(\?.*)?$/, async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify(mockNarrative),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([mockNarrative]),
        });
      }
    });

    // 3. Decision narrative revisions
    await page.route(/\/api\/v1\/rfqs\/[^/]+\/decisions\/narratives\/[^/]+\/revisions(\?.*)?$/, async (route) => {
      const payload = JSON.parse(route.request().postData() || "{}");
      const newRev = {
        id: "rev-001",
        narrative_generation_id: MOCK_NARRATIVE_ID,
        revision_number: 1,
        revised_text: payload.revised_text,
        revision_rationale: payload.revision_rationale,
        revised_by: "buyer_officer",
        created_at: new Date().toISOString(),
      };
      mockNarrative.revisions.push(newRev);
      mockNarrative.current_origin = "ai_generated_human_revised";
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(newRev),
      });
    });

    // 4. Current award
    await page.route(/\/api\/v1\/rfqs\/[^/]+\/decisions\/awards\/current/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "null",
      });
    });

    // 5. Awards list & draft creation (exact path)
    await page.route(/\/api\/v1\/rfqs\/[^/]+\/decisions\/awards(\?.*)?$/, async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: MOCK_AWARD_ID,
            rfq_id: MOCK_RFQ_ID,
            scoring_run_id: MOCK_RUN_ID,
            awarded_supplier_id: "supp-alpha",
            awarded_supplier_name: "Supplier Alpha",
            awarded_supplier_rank: 1,
            current_status: "draft",
            created_by: "buyer_admin",
            created_at: new Date().toISOString(),
            events: [],
            is_based_on_latest_run: true,
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      }
    });

    // 6. Award confirmation
    await page.route(/\/api\/v1\/rfqs\/[^/]+\/decisions\/awards\/[^/]+\/confirm/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: MOCK_AWARD_ID,
          rfq_id: MOCK_RFQ_ID,
          scoring_run_id: MOCK_RUN_ID,
          awarded_supplier_id: "supp-alpha",
          awarded_supplier_name: "Supplier Alpha",
          awarded_supplier_rank: 1,
          current_status: "confirmed",
          provenance_hash: "hash_award_123",
          created_by: "buyer_admin",
          created_at: new Date().toISOString(),
          events: [
            {
              id: "evt-1",
              award_decision_id: MOCK_AWARD_ID,
              event_type: "draft_created",
              event_number: 1,
              event_payload: { justification: "Approved Rank 1" },
              actor_principal: "buyer_admin",
              created_at: new Date().toISOString(),
            },
            {
              id: "evt-2",
              award_decision_id: MOCK_AWARD_ID,
              event_type: "confirmed",
              event_number: 2,
              event_payload: {},
              actor_principal: "buyer_admin",
              created_at: new Date().toISOString(),
            },
          ],
          is_based_on_latest_run: true,
        }),
      });
    });

    // 7. Single RFQ Detail
    await page.route(/\/api\/v1\/rfqs\/[^/?]+(\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockRFQDetail),
      });
    });

    // 8. RFQs list
    await page.route(/\/api\/v1\/rfqs(\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: mockRFQsList, total: 1, page: 1, page_size: 10, pages: 1 }),
      });
    });
  });

  test("renders decision workspace with narrative and grounded claims", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/decisions`);

    // Verify main headings
    await expect(page.locator("h1")).toContainText("Evidence-Backed Decision & Award Workflow");
    await expect(page.getByText("Human Decision Pending")).toBeVisible();

    // Verify narrative card is rendered
    await expect(page.getByText(/decision support memo #1/i)).toBeVisible();
    await expect(page.getByText("Supplier Alpha is the highest-ranked vendor")).toBeVisible();

    // Verify grounded claims
    await expect(page.getByText("Supplier Alpha achieved a total score of 88.5000")).toBeVisible();

    // Click on grounded claim to open Fact Reference modal
    await page.getByText("Supplier Alpha achieved a total score of 88.5000").click();
    await expect(page.getByText("Claim Fact Reference #0")).toBeVisible();
    await expect(page.getByText("Deterministic Fact References:")).toBeVisible();

    // Close claim details modal
    await page.getByRole("button", { name: "Close" }).click();
  });

  test("human revision workflow records append-only correction", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/decisions`);

    // Click Revise Narrative
    await page.getByRole("button", { name: "Revise Narrative" }).click();
    await expect(page.getByText("Create Human Revision")).toBeVisible();

    // Fill revision fields
    const revisedTextarea = page.locator("textarea[placeholder*='Enter corrected narrative']");
    await revisedTextarea.fill("Committee formal statement: Supplier Alpha selected for comprehensive superiority.");

    const rationaleInput = page.locator("input[placeholder*='e.g. Corrected']");
    await rationaleInput.fill("Aligned executive summary with procurement committee vote.");

    // Submit revision
    await page.getByRole("button", { name: "Save Revision" }).click();

    // Verify revised text displayed
    await expect(page.getByText("Latest Human Revision")).toBeVisible();
    await expect(page.getByText("Aligned executive summary with procurement committee vote.")).toBeVisible();
  });

  test("human award confirmation modal requires checklist acknowledgements and Rank 2 rationale", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/decisions`);

    // Open Award modal
    await page.getByRole("button", { name: "Draft & Confirm Award Decision" }).click();
    await expect(page.getByText("Human Procurement Award Decision")).toBeVisible();

    // Verify Rank #1 is displayed as contextual scoring information only (not pre-selected)
    await expect(page.getByText("Deterministic Top-Scored Supplier (Context Only)")).toBeVisible();

    // Check submit button is disabled initially (no supplier selected)
    const confirmBtn = page.getByRole("button", { name: "Confirm & Award RFQ" });
    await expect(confirmBtn).toBeDisabled();

    // Fill justification
    await page.locator("textarea[placeholder*='Provide commercial']").fill("Evaluation complete.");

    // Check all three governance checkboxes
    await page.getByText("I have reviewed the deterministic scoring calculations").click();
    await page.getByText("I confirm that technical compliance and commercial quotation").click();
    await page.getByText("I understand this human action transitions the RFQ to DECIDED").click();

    // Button is STILL disabled because NO supplier is selected
    await expect(confirmBtn).toBeDisabled();

    // Scope selectors to the Award Modal
    const modal = page.locator(".glass-panel").filter({ hasText: "Human Procurement Award Decision" });

    // Select Supplier Beta (Rank #2) inside modal
    await modal.getByText("Supplier Beta", { exact: true }).click();

    // Mandatory Non-Rank #1 governance warning appears
    await expect(page.getByText("Non-Rank #1 Selection Governance Rule")).toBeVisible();
    // Button is STILL disabled because nonRank1Rationale is empty
    await expect(confirmBtn).toBeDisabled();

    // Fill Non-Rank #1 mandatory rationale
    const nonRank1Area = page.locator("textarea[placeholder*='Mandatory rationale for selecting non-Rank #1']");
    await nonRank1Area.fill("Strategic dual-sourcing requirement and superior lead-time guarantee.");
    await expect(confirmBtn).toBeEnabled();

    // Switch selection to Supplier Alpha (Rank #1) inside modal
    await modal.getByText("Supplier Alpha", { exact: true }).click();
    // Non-Rank #1 warning disappears (no deviation rationale required for Rank 1)
    await expect(page.getByText("Non-Rank #1 Selection Governance Rule")).not.toBeVisible();
    await expect(confirmBtn).toBeEnabled();

    // Submit award
    await confirmBtn.click();

    // Modal closes
    await expect(page.getByText("Human Procurement Award Decision")).not.toBeVisible();
  });

  test("passes accessibility checks on decision workspace", async ({ page }) => {
    await page.goto(`/rfqs/${MOCK_RFQ_ID}/decisions`);
    await page.waitForSelector("h1");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .disableRules(["color-contrast"]) // dark theme custom glass tokens
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });
});
