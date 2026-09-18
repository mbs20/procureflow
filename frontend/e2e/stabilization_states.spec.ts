import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const rfq = {id:'stabilization-rfq',title:'Synthetic RFQ',reference_currency:'USD',status:'draft'};
const criterion = {criterion_id:'price',name:'Price',weight:'1',direction:'lower_is_better',source_field:'normalized_comparable_total',source_type:'price'};
const config = {id:'config',name:'Price model',version:1,rfq_id:rfq.id,config_payload:{criteria:[criterion]},is_active:true};
const snapshot = {id:'snapshot',rfq_id:rfq.id,snapshot_version:1,title:'Approved baseline'};
const supplier = {quotation_id:'supplier',supplier_name:'Synthetic supplier',eligibility_status:'eligible',total_score:'100.0000',rank:1,knockout_reasons:[],criteria_breakdown:[]};

for (const scenario of ['no-snapshot','no-config','valid','existing','invalid-run','validation-error']) {
 test(`scoring prerequisite state: ${scenario}`,async({page})=>{
  const crashes:string[]=[]; page.on('pageerror',e=>crashes.push(e.message));
  await page.route('**/api/v1/**', async route=>{
   const url=new URL(route.request().url()); let body:unknown=[]; let status=200;
   if(url.pathname.endsWith('/rfqs'))body={items:[rfq],total:1};
   else if(url.pathname.endsWith('/snapshots'))body=scenario==='no-snapshot'?[]:[snapshot];
   else if(url.pathname.endsWith('/configurations/active')) {body=config; if(scenario==='no-config')status=404;}
   else if(url.pathname.endsWith('/runs'))body=scenario==='existing'?[{id:'run',snapshot_id:'snapshot',configuration_id:'config',results_payload:{suppliers:[supplier]}}]:scenario==='invalid-run'?[{id:'run',results_payload:{}}]:[];
   else if(url.pathname.endsWith('/simulate')) {body=[supplier];if(scenario==='validation-error'){status=422;body={detail:[{loc:['body','snapshot_id'],msg:'Field required'}]};}}
   await route.fulfill({status,json:body});
  });
  await page.goto(`/rfqs/${rfq.id}/scoring`);
  await expect(page.getByRole('heading',{level:1})).toBeVisible();
  if(scenario==='no-snapshot')await expect(page.getByText('No valid comparison snapshot is available.')).toBeVisible();
  if(scenario==='no-config')await expect(page.getByRole('button',{name:'Create a price-only configuration'})).toBeVisible();
  if(['valid','existing'].includes(scenario))await expect(page.getByRole('cell',{name:/^Synthetic supplier ID:/})).toBeVisible();
  if(scenario==='invalid-run')await expect(page.getByText(/scoring results/i)).toBeVisible();
  if(scenario==='validation-error')await expect(page.getByText(/Field required/)).toBeVisible();
  await expect(page.getByText('[object Object]',{exact:false})).toHaveCount(0);
  expect(crashes).toEqual([]);
 });
}

test('narrow navigation leaves main content accessible',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.route('**/api/v1/rfqs?*',route=>route.fulfill({json:{items:[],total:0}}));
 await page.goto('/rfqs');
 const main=await page.locator('main').boundingBox();
 expect(main!.width).toBeGreaterThan(330);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze();
 expect(results.violations).toEqual([]);
});
