import { dailyLimitFor } from './budget.ts';
import { weeklyCapMicros, XAI_USD } from './xai-usd.ts';

/**
 * Live AI completions through Cloudflare AI Gateway.
 * The gateway only logs. The spend-budget counter remains the budget.
 * XAI_API_KEY is a secret name, read here to authorize the gateway request
 * and never logged or forwarded. Workers AI uses the [ai] binding.
 */

export const XAI_HOST = 'ai.xai';
export const WORKERS_AI_HOST = 'ai.workers';
export const DEFAULT_XAI_MODEL = 'grok-4';
/** Closest current id. llama-3.1-8b-instruct-fast is not in the catalog. */
export const DEFAULT_WORKERS_AI_MODEL = '@cf/meta/llama-3.1-8b-instruct-fp8';
export const WORKERS_AI_MAX_INPUT_CHARS = 4000;
export const WORKERS_AI_MAX_OUTPUT_TOKENS = 160;
export const GATEWAY_ORIGIN = 'https://gateway.ai.cloudflare.com';
const ID_PATTERN = /^[A-Za-z0-9_-]+$/;

export interface ChatMessage {
	role: string;
	content: string;
}

export interface GatewayRunOptions {
	gateway: { id: string; skipCache: true };
}

export interface WorkersAiBinding {
	run(
		model: string,
		input: { messages: ChatMessage[]; max_tokens: number },
		options: GatewayRunOptions,
	): Promise<unknown>;
}

export interface ProviderEnv {
	XAI_API_KEY?: string;
	XAI_ENABLED?: string;
	XAI_MODEL?: string;
	WORKERS_AI_MODEL?: string;
	CF_ACCOUNT_ID?: string;
	AI_GATEWAY_ID?: string;
	XAI_WEEKLY_USD_CAP?: string;
	AI?: WorkersAiBinding;
}

export interface GatewayCall {
	provider?: string;
	url?: string | null;
	gateway_id?: string | null;
}

export function xaiGatewayUrl(accountId: string | undefined, gatewayId: string | undefined): string | null {
	const account = (accountId ?? '').trim();
	const gateway = (gatewayId ?? '').trim();
	if (!ID_PATTERN.test(account) || !ID_PATTERN.test(gateway)) return null;
	return `${GATEWAY_ORIGIN}/v1/${account}/${gateway}/grok/v1/chat/completions`;
}

export function isGatewayXaiUrl(url: string): boolean {
	let parsed: URL;
	try {
		parsed = new URL(url);
	} catch {
		return false;
	}
	if (parsed.origin !== GATEWAY_ORIGIN || parsed.search || parsed.username || parsed.password) {
		return false;
	}
	const parts = parsed.pathname.split('/').filter(Boolean);
	if (parts.length !== 7) return false;
	const [version, account, gateway, provider, apiVersion, chat, completions] = parts;
	return version === 'v1'
		&& ID_PATTERN.test(account)
		&& ID_PATTERN.test(gateway)
		&& provider === 'grok'
		&& apiVersion === 'v1'
		&& chat === 'chat'
		&& completions === 'completions';
}

/** Non-empty when this recorded call skipped the gateway URL or binding. */
export function gatewayBypassErrors(call: GatewayCall): string[] {
	if (call.provider === 'xai') {
		const url = (call.url ?? '').trim();
		if (!isGatewayXaiUrl(url)) return ['xAI call bypasses the gateway URL'];
		return [];
	}
	if (call.provider === 'workers_ai') {
		const gatewayId = (call.gateway_id ?? '').trim();
		if (!ID_PATTERN.test(gatewayId)) return ['Workers AI call bypasses the gateway binding'];
		return [];
	}
	return [`unknown AI provider ${call.provider || '(missing)'}`];
}

function workersGatewayOptions(gatewayId: string | undefined): GatewayRunOptions | null {
	const id = (gatewayId ?? '').trim();
	if (!ID_PATTERN.test(id)) return null;
	return { gateway: { id, skipCache: true } };
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

export function xaiCompletionBody(model: string, messages: ChatMessage[]): {
	model: string;
	messages: ChatMessage[];
	max_tokens: number;
} {
	return { model, messages, max_tokens: XAI_USD.max_output_tokens };
}

export function clipMessages(messages: ChatMessage[], maxChars: number): ChatMessage[] {
	let remaining = maxChars;
	const out: ChatMessage[] = [];
	for (const message of messages) {
		if (remaining <= 0) break;
		const content = message.content.slice(0, remaining);
		remaining -= content.length;
		if (!content) continue;
		out.push({ role: message.role, content });
	}
	return out;
}

function xaiEnabled(env: ProviderEnv): boolean {
	return ['1', 'true', 'yes', 'on'].includes((env.XAI_ENABLED ?? '').trim().toLowerCase());
}

export async function completeXai(
	env: ProviderEnv,
	messages: ChatMessage[],
	fetchImpl: FetchImpl = fetch,
): Promise<Response> {
	const key = env.XAI_API_KEY;
	const url = xaiGatewayUrl(env.CF_ACCOUNT_ID, env.AI_GATEWAY_ID);
	// The gateway URL is computed so the path stays in this file. A hard daily
	// budget of 0, a weekly dollar cap of 0, or the default-off provider
	// returns before fetch.
	const weeklyClosed = weeklyCapMicros(env.XAI_WEEKLY_USD_CAP) === 0;
	if (!xaiEnabled(env) || dailyLimitFor('xai', env) === 0 || weeklyClosed || !key || !url || !isGatewayXaiUrl(url)) {
		return jsonResult({ ok: false, error: 'disabled' }, 503);
	}
	const model = env.XAI_MODEL?.trim() || DEFAULT_XAI_MODEL;
	let upstream: Response;
	try {
		upstream = await fetchImpl(url, {
			method: 'POST',
			headers: {
				authorization: `Bearer ${key}`,
				'content-type': 'application/json',
				'cf-aig-skip-cache': 'true',
			},
			body: JSON.stringify(xaiCompletionBody(model, messages)),
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
	const options = workersGatewayOptions(env.AI_GATEWAY_ID);
	if (!env.AI || !options) return jsonResult({ ok: false, error: 'unconfigured' }, 503);
	const model = env.WORKERS_AI_MODEL?.trim() || DEFAULT_WORKERS_AI_MODEL;
	const input = {
		messages: clipMessages(messages, WORKERS_AI_MAX_INPUT_CHARS),
		max_tokens: WORKERS_AI_MAX_OUTPUT_TOKENS,
	};
	let payload: unknown;
	try {
		payload = await env.AI.run(model, input, options);
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
