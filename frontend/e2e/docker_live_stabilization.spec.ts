import {test, expect} from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
const api = 'http://localhost:8000/api/v1';
const headers = {'X-API-Key': 'procureflow_dev_api_key_12345'};
test('Docker production PDF canvas, CSV download and original document identity', async ({page, request}) => {
 test.setTimeout(60000);

 // Verify live Docker production stack availability (FastAPI backend on :8000 and Nginx frontend on :5173)
 let dockerLive = false;
 try {
  const [backendHealth, frontendRes] = await Promise.all([
   request.get(`${api}/health`, { timeout: 4000 }),
   request.get("http://localhost:5173/", { timeout: 4000 }),
  ]);
  const serverHeader = (frontendRes.headers()["server"] || "").toLowerCase();
  dockerLive = backendHealth.status() === 200 && serverHeader.includes("nginx");
 } catch {
  dockerLive = false;
 }
 test.skip(!dockerLive, "Live Docker production stack (Nginx frontend on :5173 and backend on :8000) is not available.");

 const production = await request.get("http://localhost:5173/");
 expect(production.headers()["server"]).toContain("nginx");
 const description = '=SUM(1,2) "\u00e9quipement"\nSeconde ligne';
 const rfqResponse = await request.post(`${api}/rfqs`, {headers, data: {title: 'Runtime export and PDF regression', reference_currency: 'USD', line_items: [{position: 1, description, quantity: 10, unit: 'pcs'}], criteria: []}});
 expect(rfqResponse.status()).toBe(201);
 const rfq = await rfqResponse.json();
 const upload = await request.post(`${api}/quotations/upload`, {headers, multipart: {rfq_id: rfq.id, supplier_name: 'Runtime PDF supplier', file: {name: 'native_valves.pdf', mimeType: 'application/pdf', buffer: fs.readFileSync(path.resolve('../backend/tests/fixtures/quotations/native_valves.pdf'))}}});
 expect(upload.status()).toBe(201);
 const quote = await upload.json();
 expect((await request.post(`${api}/quotations/${quote.id}/extract`, {headers})).ok()).toBe(true);
 let extraction: any;
 await expect.poll(async () => {
  const response = await request.get(`${api}/quotations/${quote.id}/extractions/latest`);
  if (response.ok()) extraction = await response.json();
  return extraction?.line_items?.length || 0;
 }).toBeGreaterThan(0);
 const worker = page.waitForResponse(r => r.url().includes('pdf.worker') && r.status() === 200);
 await page.goto(`/quotations/${quote.id}/review`);
 const workerResponse = await worker;
 expect(workerResponse.headers()['content-type']).toContain('javascript');
 expect(workerResponse.headers()['x-content-type-options']).toBe('nosniff');
 await expect(page.locator('canvas')).toBeVisible();
 await expect.poll(() => page.locator('canvas').evaluate((c: HTMLCanvasElement) => c.width)).toBeGreaterThan(300);
 for (const [index, item] of extraction.line_items.entries()) {
  if (index === 0) expect((await request.patch(`${api}/quotations/${quote.id}/line-items/${item.id}`, {headers, data: {rfq_line_item_id: rfq.line_items[0].id}})).ok()).toBe(true);
  else expect((await request.delete(`${api}/quotations/${quote.id}/line-items/${item.id}`, {headers})).ok()).toBe(true);
 }
 expect((await request.patch(`${api}/quotations/${quote.id}/status`, {headers, data: {status: 'approved'}})).ok()).toBe(true);
 await page.goto(`/rfqs/${rfq.id}/matrix`);
 await expect(page.getByText('Runtime PDF supplier').first()).toBeVisible();
 const downloadPromise = page.waitForEvent('download');
 await page.getByRole('button', {name: /Export CSV/i}).click();
 const download = await downloadPromise;
 expect(download.suggestedFilename()).toBe(`comparison_matrix_${rfq.id}.csv`);
 const csv = fs.readFileSync((await download.path())!, 'utf8');
 expect(csv.length).toBeGreaterThan(100);
 expect(csv).toContain('"\'=SUM(1,2) ""\u00e9quipement""\nSeconde ligne"');
 await page.locator('td.cursor-pointer').first().click();
 const link = page.getByRole('link', {name: /View Original Document/i});
 const href = await link.getAttribute('href');
 expect(href).toBe(`/api/v1/quotations/${quote.id}/documents/${quote.documents[0].id}/download`);
 const response = await request.get(`http://localhost:5173${href}`);
 expect(response.status()).toBe(200);
 expect((await response.body()).subarray(0, 5).toString()).toBe('%PDF-');
 // Headless Chromium hands PDF navigation to its internal viewer; assert the
 // actual navigation response rather than that viewer's opaque popup URL.
 const navigation = page.context().waitForEvent('response', r => r.url() === `http://localhost:5173${href}` && r.request().isNavigationRequest());
 await link.click();
 const openedDocument = await navigation;
 expect(openedDocument.status()).toBe(200);
 expect(openedDocument.headers()['content-type']).toContain('application/pdf');
});
