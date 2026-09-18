import { test, expect } from '@playwright/test';

test('balanced RFQ preset satisfies native validation and submits', async ({ page }) => {
  let submitted: any;
  await page.route('**/api/v1/rfqs', async route => {
    submitted = route.request().postDataJSON();
    await route.fulfill({ json: { id: 'created' } });
  });
  await page.goto('/e2e/fixtures/forms.html');
  await page.getByPlaceholder(/High-Pressure/).fill('Preset regression');
  await page.getByRole('button', { name: /Balanced Preset/ }).click();
  expect(await page.locator('form').evaluate((form: HTMLFormElement) => form.checkValidity())).toBe(true);
  await page.locator('button[type=submit]').click();
  await expect.poll(() => submitted?.criteria?.map((c: any) => c.weight)).toEqual([0.4, 0.3, 0.2, 0.1]);
});

test('review decimal strings remain editable and zero lead time and audit reason are preserved', async ({ page }) => {
  await page.goto('/e2e/fixtures/forms.html?kind=edit');
  await page.locator('#edit-reason').fill('Verify decimal extraction');
  await page.locator('button[type=submit]').click();
  await expect.poll(() => page.evaluate(() => (window as any).saved)).toEqual({ id: '1', reason: 'Verify decimal extraction', patch: expect.objectContaining({ quantity: 2.5, unit_price: 10.25, total_price: 25.625, lead_time_days: 0 }) });
});

for (const kind of ['add', 'edit']) {
  test(`${kind} rejects missing quantity and fractional lead time without silently coercing`, async ({ page }) => {
    await page.goto(`/e2e/fixtures/forms.html?kind=${kind}`);
    if (kind === 'edit') await page.locator('#edit-reason').fill('Correct extraction');
    else await page.locator('input[type=text]').first().fill('Valve');
    const numeric = page.locator('input[type=number]');
    await numeric.nth(0).fill('');
    // Exercise handler validation too; native required validation must not be the only guard.
    await page.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    expect(await page.evaluate(() => (window as any).saved)).toBeUndefined();
    await expect(page.getByText(/valid numeric/i)).toBeVisible();
    await numeric.nth(0).fill('2.5');
    await numeric.nth(1).fill('');
    await page.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    expect(await page.evaluate(() => (window as any).saved)).toBeUndefined();
    await numeric.nth(1).fill('10.25');
    await numeric.last().fill('1.5');
    await page.locator('form').evaluate(form => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })));
    expect(await page.evaluate(() => (window as any).saved)).toBeUndefined();
    await numeric.last().fill('0');
    await page.locator('button[type=submit]').click();
    await expect.poll(() => page.evaluate(() => (window as any).saved)).toBeTruthy();
  });
}

test('edit requires a meaningful audit reason', async ({ page }) => {
  await page.goto('/e2e/fixtures/forms.html?kind=edit');
  await page.locator('#edit-reason').fill('   ');
  await page.locator('button[type=submit]').click();
  await expect(page.getByText('Enter a reason for this correction.')).toBeVisible();
  expect(await page.evaluate(() => (window as any).saved)).toBeUndefined();
});
