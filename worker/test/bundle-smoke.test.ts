import assert from 'node:assert/strict';
import { test } from 'node:test';
import worker, { CfbApiContainer, ContainerProxy } from '../../.wrangler/tested/index.js';

function smokeEnv() {
	return {
		API_RATE_LIMITER: { async limit() { return { success: true }; } },
		AGENT_RATE_LIMITER: { async limit() { return { success: true }; } },
		ASSETS: { async fetch() { return new Response('no', { status: 404 }); } },
		CFB_API: {
			idFromName() { return 'id'; },
			get() {
				return { async fetch() { throw new Error('container'); } };
			},
		},
	};
}

test('tested bundle exports the worker entry', () => {
	assert.equal(typeof worker.fetch, 'function');
	assert.equal(typeof ContainerProxy, 'function');
	assert.equal(typeof CfbApiContainer, 'function');
	assert.deepEqual(
		Object.keys(CfbApiContainer.outboundByHost).sort(),
		['ai.workers', 'ai.xai', 'spend.budget'],
	);
});

test('tested bundle answers /api without starting the container', async () => {
	const response = await worker.fetch(
		new Request('https://preview.example.workers.dev/api'),
		smokeEnv() as never,
	);
	assert.equal(response.status, 404);
	assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
});
