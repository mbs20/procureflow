import { describe, it, expect, vi, afterEach } from 'vitest';
import { fetchActiveScoringConfiguration, fetchScoringRuns, simulateScoring, createScoringConfiguration, runSensitivityAnalysis } from '../../api/scoring';

const criterion = { criterion_id: 'price', name: 'Price', weight: '1.0000', direction: 'lower_is_better', source_type: 'price', source_field: 'normalized_comparable_total' };
const supplier = { quotation_id: 'q1', supplier_name: 'Synthetic supplier', eligibility_status: 'eligible', total_score: '100.0000', exact_total_score: '100', rank: 1, knockout_reasons: [], criteria_breakdown: [{ criterion_id: 'price', criterion_name: 'Price', raw_value: '120.25', exact_raw_value: '120.25', source_path: 'suppliers.q1.normalized_comparable_total', normalized_score: '100', weight: '1', weighted_contribution: '100', is_knockout_applied: false, formula_audit: 'equal cohort', min_value: '120.25', max_value: '120.25' }] };
function reply(data: unknown, status=200) { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(data), {status}))); }
afterEach(()=>vi.unstubAllGlobals());
describe('actual backend scoring contract', ()=>{
 it('reads criteria inside config_payload and decimal strings', async()=>{ reply({id:'c1',rfq_id:'r1',version:1,name:'Config',config_payload:{criteria:[criterion]}}); const c=await fetchActiveScoringConfiguration('r1'); expect(c?.criteria[0].weight).toBe(1); });
 it('reads frozen suppliers without losing evidence',async()=>{ reply([{id:'run',rfq_id:'r1',snapshot_id:'s1',configuration_id:'c1',results_payload:{suppliers:[supplier]}}]); const [run]=await fetchScoringRuns('r1'); expect(run.scores[0].composite_score).toBe(100); expect(run.scores[0].breakdown.Price.source_path).toContain('q1'); expect(run.comparison_snapshot_id).toBe('s1'); });
 it('uses actual simulation request and array response',async()=>{ reply([supplier]); const result=await simulateScoring('r1',{comparison_snapshot_id:'s1',scoring_configuration_id:'c1'}); expect(result.scores[0].composite_score).toBe(100); expect(JSON.parse((fetch as any).mock.calls[0][1].body)).toMatchObject({snapshot_id:'s1',configuration_id:'c1'}); });
 it('sends backend criterion IDs and directions',async()=>{ reply({id:'c1',version:1,config_payload:{criteria:[criterion]}}); await createScoringConfiguration('r1',{name:'Config',criteria:[{name:'Price',weight:1,direction:'MINIMIZE',source_field:'normalized_comparable_total'}]}); const body=JSON.parse((fetch as any).mock.calls[0][1].body); expect(body.criteria[0].criterion_id).toBeTruthy(); expect(body.criteria[0].direction).toBe('lower_is_better'); });
 it('rejects malformed results instead of exposing undefined scores',async()=>{ reply([{id:'run',results_payload:{}}]); await expect(fetchScoringRuns('r1')).rejects.toThrow(/scoring/i); });
 it('does not stringify structured validation errors as object Object',async()=>{ reply({detail:[{loc:['body','snapshot_id'],msg:'Field required'}]},422); await expect(simulateScoring('r1',{comparison_snapshot_id:'s1'})).rejects.toThrow('Field required'); });
});

describe('scoring response validation', () => {
 it.each(['unknown_status', '', null])('rejects invalid eligibility %s', async (status) => {
  reply([{ id: 'run', snapshot_id: 's1', results_payload: { suppliers: [{ ...supplier, eligibility_status: status }] } }]);
  await expect(fetchScoringRuns('r1')).rejects.toThrow(/scoring/i);
 });
 it.each([true, '', 'NaN', null])('rejects invalid numeric scores %s', async (value) => {
  reply([{ id: 'run', snapshot_id: 's1', results_payload: { suppliers: [{ ...supplier, total_score: value }] } }]);
  await expect(fetchScoringRuns('r1')).rejects.toThrow(/scoring/i);
 });
 it('retains blocked eligibility and null rank', async () => {
  reply([{id:'run', snapshot_id:'s1', results_payload:{suppliers:[{...supplier, eligibility_status:'missing_value_blocked', rank:null}]}}]);
  const [run] = await fetchScoringRuns('r1');
  expect(run.scores[0]).toMatchObject({status:'missing_value_blocked', is_eligible:false, rank:null});
 });
 it('rejects fractional rankings', async () => {
  reply([{id:'run', snapshot_id:'s1', results_payload:{suppliers:[{...supplier, rank:1.5}]}}]);
  await expect(fetchScoringRuns('r1')).rejects.toThrow(/scoring/i);
 });
 it('converts sensitivity decimals, preserves null rankings and infeasible breakeven', async () => {
  reply({swept_criterion_id:'price', points:[{weight:'0.5', redistributed_weights:{price:'0.5'},supplier_scores:{q1:'90'},rankings:{q1:null}}], crossover_points:[], breakeven:{candidate_id:'q1', candidate_name:'Supplier', target_rank:1,current_price:'10',required_price:null,delta_price:null,delta_pct:null,feasible:false,convergence_steps:0,notes:'Not feasible'}});
  const result = await runSensitivityAnalysis('r1',{comparison_snapshot_id:'s1',sweep_criterion:'price'});
  expect(result.data_points[0]).toEqual({weight:0.5,weights_vector:{price:0.5},supplier_scores:{q1:90},ranks:{q1:null}});
  expect(result.breakeven).toMatchObject({is_feasible:false,required_price:null,current_price:10});
 });
 it('rejects invalid criteria directions', async () => {
  reply({id:'c1',version:1,config_payload:{criteria:[{...criterion,direction:'sideways'}]}});
  await expect(fetchActiveScoringConfiguration('r1')).rejects.toThrow(/scoring/i);
 });
 it('handles non-object API errors', async () => {
  reply(null,500);
  await expect(fetchScoringRuns('r1')).rejects.toThrow('Failed to fetch scoring runs');
 });
 it('accepts unranked zero only in legacy sensitivity presentation payloads', async () => {
  reply({sweep_criterion:'Price',data_points:[{weight:1,weights_vector:{Price:1},supplier_scores:{q1:0},ranks:{q1:0}}],crossover_points:[]});
  const result = await runSensitivityAnalysis('r1',{comparison_snapshot_id:'s1',sweep_criterion:'price'});
  expect(result.data_points[0].ranks.q1).toBeNull();
  reply({swept_criterion_id:'price',points:[{weight:1,redistributed_weights:{price:1},supplier_scores:{q1:0},rankings:{q1:0}}],crossover_points:[]});
  await expect(runSensitivityAnalysis('r1',{comparison_snapshot_id:'s1',sweep_criterion:'price'})).rejects.toThrow(/rank/);
 });
});
