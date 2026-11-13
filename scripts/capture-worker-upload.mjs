/**
 * Record Worker module bodies from the FormData wrangler builds on deploy.
 * wrangler 4.156.0 calls createWorkerUploadForm({ dryRun: true }) and puts
 * each module body in a File. dryRun does not change those bodies.
 * The wrangler bin re-spawns cli.js with process.execArgv, so --import
 * reaches that process.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

const outDir = process.env.WORKER_UPLOAD_FORM_DIR;
const MODULE_TYPES = new Set([
	'application/javascript+module',
	'application/javascript',
	'application/wasm',
	'application/octet-stream',
	'text/plain',
	'text/x-python',
	'text/x-python-requirement',
]);

if (outDir) {
	const Original = globalThis.File;
	globalThis.File = class WorkerUploadFile extends Original {
		constructor(bits, name, options) {
			super(bits, name, options);
			const type = this.type || options?.type || '';
			if (!MODULE_TYPES.has(type)) return;
			const chunks = [];
			for (const bit of bits ?? []) {
				if (typeof bit === 'string') chunks.push(Buffer.from(bit));
				else if (bit instanceof ArrayBuffer) chunks.push(Buffer.from(bit));
				else if (ArrayBuffer.isView(bit)) chunks.push(Buffer.from(bit.buffer, bit.byteOffset, bit.byteLength));
				else chunks.push(Buffer.from(bit));
			}
			const dest = join(outDir, String(name));
			mkdirSync(dirname(dest), { recursive: true });
			writeFileSync(dest, Buffer.concat(chunks));
		}
	};
}
