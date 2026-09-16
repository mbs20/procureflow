import { chromium } from "@playwright/test";
import fs from "fs";
import path from "path";

const BASE_URL = "http://localhost:5173";
const API_BASE = "http://localhost:8000/api/v1";
const DEV_HEADERS = { "X-API-Key": "procureflow_dev_api_key_12345" };

async function run() {
  const repoRoot = path.resolve(process.cwd(), "..");
  const assetsDir = path.join(repoRoot, "docs/assets/screenshots");
  const framesDir = path.join(repoRoot, "docs/assets/frames");
  fs.mkdirSync(assetsDir, { recursive: true });
  fs.mkdirSync(framesDir, { recursive: true });

  console.log("Fetching seeded demo RFQ...");
  const rfqsRes = await fetch(`${API_BASE}/rfqs`, { headers: DEV_HEADERS });
  const rfqsData = await rfqsRes.json();
  const rfqsList = rfqsData.items || rfqsData;
  const demoRfq = rfqsList.find((r: any) => r.title.includes("[DEMO]"));

  if (!demoRfq) {
    throw new Error("Demo RFQ not found. Please run seed_demo script first.");
  }
  const rfqId = demoRfq.id;
  console.log(`Found demo RFQ: ${demoRfq.title} (${rfqId})`);

  const quotesRes = await fetch(`${API_BASE}/quotations?rfq_id=${rfqId}`, { headers: DEV_HEADERS });
  const quotesData = await quotesRes.json();
  const quotesList = Array.isArray(quotesData) ? quotesData : (quotesData.items || quotesData.value || []);
  const apexQuote = quotesList.find((q: any) => q.supplier_name.includes("Apex")) || quotesList[0];

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 2,
    colorScheme: "dark",
  });
  const page = await context.newPage();

  console.log("Capturing Screenshot 1: RFQ & Ingestion Status...");
  await page.goto(`${BASE_URL}/rfqs/${rfqId}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(assetsDir, "01_rfq_and_ingestion.png") });

  console.log("Capturing Screenshot 2: Human Review Split-Pane Workspace...");
  await page.goto(`${BASE_URL}/quotations/${apexQuote.id}/review`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  // Highlight an evidence row if available
  const evidenceBtn = page.locator("button:has-text('View Evidence'), tr:has-text('Industrial High-Pressure Gate Valve'), tr:has-text('High-Pressure Gate Valve')").first();
  if (await evidenceBtn.isVisible()) {
    await evidenceBtn.click();
    await page.waitForTimeout(800);
  }
  await page.screenshot({ path: path.join(assetsDir, "02_human_review_split_pane.png") });

  console.log("Capturing Screenshot 3: Multi-Supplier Comparison Matrix...");
  await page.goto(`${BASE_URL}/rfqs/${rfqId}/matrix`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(assetsDir, "03_comparison_matrix_normalization.png") });

  console.log("Capturing Screenshot 4: Deterministic Scoring & Sensitivity Sweep...");
  await page.goto(`${BASE_URL}/rfqs/${rfqId}/scoring`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(assetsDir, "04_deterministic_scoring_sensitivity.png") });

  console.log("Capturing Screenshot 5: Grounded Decision Narrative & Award Workflow...");
  await page.goto(`${BASE_URL}/rfqs/${rfqId}/decisions`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(assetsDir, "05_grounded_decision_award_workflow.png") });

  console.log("Capturing Hero Demo GIF Frames...");
  // Step A: Review workspace
  await page.goto(`${BASE_URL}/quotations/${apexQuote.id}/review`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(framesDir, "frame_01.png") });

  // Step B: Click value to reveal bounding box
  if (await evidenceBtn.isVisible()) {
    await evidenceBtn.click();
    await page.waitForTimeout(800);
  }
  await page.screenshot({ path: path.join(framesDir, "frame_02.png") });
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(framesDir, "frame_03.png") });

  // Step C: Navigate to Comparison Matrix
  await page.goto(`${BASE_URL}/rfqs/${rfqId}/matrix`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(framesDir, "frame_04.png") });
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(framesDir, "frame_05.png") });

  // Step D: Navigate to Scoring & Formulas
  await page.goto(`${BASE_URL}/rfqs/${rfqId}/scoring`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(framesDir, "frame_06.png") });
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(framesDir, "frame_07.png") });

  await browser.close();
  console.log("Screenshots and frames captured successfully!");
}

run().catch((err) => {
  console.error("Asset generation error:", err);
  process.exit(1);
});
