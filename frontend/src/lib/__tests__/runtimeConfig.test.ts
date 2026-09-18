import { readFileSync } from 'node:fs';
import { expect, test } from 'vitest';
test('nginx resolves recreated backend and serves PDF modules securely',()=>{
 const config=readFileSync('nginx.conf','utf8');
 expect(config).toContain('resolver 127.0.0.11');
 expect(config).toContain('proxy_pass $backend_upstream');
 expect(config).toMatch(/application\/javascript\s+mjs/);
 expect(config).toContain('nosniff');
 expect(config).toContain('client_max_body_size 51m');
});
test('worker health checks this worker rather than inherited HTTP',()=>{
 const compose=readFileSync('../docker-compose.yml','utf8').split('  worker:')[1].split('  frontend:')[0];
 expect(compose).toContain('inspect ping');
 expect(compose).toContain('--broker $$CELERY_BROKER_URL');
 expect(compose).not.toContain('-A procureflow.tasks.celery_app inspect');
 expect(compose).toContain('celery@$$HOSTNAME');
});
