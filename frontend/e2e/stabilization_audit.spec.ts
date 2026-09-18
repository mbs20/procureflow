import {test, expect} from '@playwright/test';
for (const language of ['en', 'fr']) {
 test(`audit shows real events and paginates in ${language}`, async ({page}) => {
  await page.addInitScript(lang => localStorage.setItem('procureflow_language', lang), language);
  await page.route('**/api/v1/audit?**', route => {
   const pageNumber = new URL(route.request().url()).searchParams.get('page');
   return route.fulfill({json: {total: 26, items: [{id: pageNumber, rfq_id: 'rfq-test', event_type: pageNumber === '1' ? 'RFQ_CREATED' : 'AWARD_REVOKED', actor_type: 'user', timestamp: '2026-09-18T10:00:00Z'}]}});
  });
  await page.goto('/audit');
  await expect(page.getByText('RFQ_CREATED')).toBeVisible();
  await page.getByRole('button', {name: language === 'fr' ? 'Suivant' : 'Next', exact: true}).click();
  await expect(page.getByText('AWARD_REVOKED')).toBeVisible();
 });
}
