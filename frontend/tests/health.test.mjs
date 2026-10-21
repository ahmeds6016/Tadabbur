import assert from 'node:assert/strict';
import { test } from 'node:test';

test('the frontend exposes a healthy uncached response for deployment smoke', async () => {
  const { GET, dynamic } = await import('../app/health/route.ts');
  const response = GET();
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: 'healthy' });
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.equal(dynamic, 'force-dynamic');
});
