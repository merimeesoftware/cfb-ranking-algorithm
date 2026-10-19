/**
 * Live AI completions. The container never sees the xAI credential.
 * Workers AI uses the Worker [ai] binding. xAI uses the XAI_API_KEY secret
 * name, read here only to authorize api.x.ai and never logged or forwarded.
 */

export const XAI_HOST = 'ai.xai';
export const WORKERS_AI_HOST = 'ai.workers';
export const DEFAULT_XAI_MODEL = 'grok-4';
export const DEFAULT_WORKERS_AI_MODEL = '@cf/meta/llama-3.1-8b-instruct';
const XAI_URL = 'https://api.x.ai/v1/chat/completions';

export interface ChatMessage {
	role: string;
	content: string;
}

export interface WorkersAiBinding {
	run(model: string, input: { messages: ChatMessage[] }): Promise<unknown>;
}

export interface ProviderEnv {
	XAI_API_KEY?: string;
	XAI_MODEL?: string;
	WORKERS_AI_MODEL?: string;
	AI?: WorkersAiBinding;
}

type FetchImpl = typeof fetch;

export function readMessages(body: unknown): ChatMessage[] | null {
	if (!body || typeof body !== 'object') return null;
	const messages = (body as { messages?: unknown }).messages;
	if (!Array.isArray(messages) || !messages.length) return null;
	const out: ChatMessage[] = [];
	for (const item of messages) {
		if (!item || typeof item !== 'object') return null;
		const role = (item as { role?: unknown }).role;
		const content = (item as { content?: unknown }).content;
		if (typeof role !== 'string' || typeof content !== 'string' || !content.trim()) return null;
		out.push({ role, content });
	}
	return out;
}

export function textFromModelPayload(payload: unknown): string {
	if (typeof payload === 'string') return payload.trim();
	if (!payload || typeof payload !== 'object') return '';
	const record = payload as {
		response?: unknown;
		result?: unknown;
		content?: unknown;
		choices?: { message?: { content?: unknown } }[];
	};
	if (typeof record.response === 'string') return record.response.trim();
	if (typeof record.result === 'string') return record.result.trim();
	if (typeof record.content === 'string') return record.content.trim();
	const choice = record.choices?.[0]?.message?.content;
	return typeof choice === 'string' ? choice.trim() : '';
}

function jsonResult(body: Record<string, unknown>, status: number): Response {
	return Response.json(body, {
		status,
		headers: { 'cache-control': 'no-store' },
	});
}

export async function completeXai(
	env: ProviderEnv,
	messages: ChatMessage[],
	fetchImpl: FetchImpl = fetch,
): Promise<Response> {
	const key = env.XAI_API_KEY;
	if (!key) return jsonResult({ ok: false, error: 'unconfigured' }, 503);
	const model = env.XAI_MODEL?.trim() || DEFAULT_XAI_MODEL;
	let upstream: Response;
	try {
		upstream = await fetchImpl(XAI_URL, {
			method: 'POST',
			headers: {
				authorization: `Bearer ${key}`,
				'content-type': 'application/json',
			},
			body: JSON.stringify({ model, messages }),
		});
	} catch {
		return jsonResult({ ok: false, error: 'upstream' }, 502);
	}
	let payload: unknown = {};
	try {
		payload = await upstream.json();
	} catch {
		payload = {};
	}
	if (!upstream.ok) return jsonResult({ ok: false, error: 'upstream' }, 502);
	const text = textFromModelPayload(payload);
	if (!text) return jsonResult({ ok: false, error: 'empty' }, 502);
	return jsonResult({ ok: true, text }, 200);
}

export async function completeWorkersAi(env: ProviderEnv, messages: ChatMessage[]): Promise<Response> {
	if (!env.AI) return jsonResult({ ok: false, error: 'unconfigured' }, 503);
	const model = env.WORKERS_AI_MODEL?.trim() || DEFAULT_WORKERS_AI_MODEL;
	let payload: unknown;
	try {
		payload = await env.AI.run(model, { messages });
	} catch {
		return jsonResult({ ok: false, error: 'upstream' }, 502);
	}
	const text = textFromModelPayload(payload);
	if (!text) return jsonResult({ ok: false, error: 'empty' }, 502);
	return jsonResult({ ok: true, text }, 200);
}

export async function completeFromRequest(
	kind: 'xai' | 'workers_ai',
	env: ProviderEnv,
	request: Request,
	fetchImpl: FetchImpl = fetch,
): Promise<Response> {
	let body: unknown;
	try {
		body = await request.json();
	} catch {
		return jsonResult({ ok: false, error: 'json' }, 400);
	}
	const messages = readMessages(body);
	if (!messages) return jsonResult({ ok: false, error: 'messages' }, 400);
	if (kind === 'xai') return completeXai(env, messages, fetchImpl);
	return completeWorkersAi(env, messages);
}
