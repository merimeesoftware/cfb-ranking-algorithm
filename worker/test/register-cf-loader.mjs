import { timingSafeEqual } from 'node:crypto';
import { register } from 'node:module';

// Workers SubtleCrypto has timingSafeEqual. Node 22's webcrypto does not.
if (typeof crypto.subtle.timingSafeEqual !== 'function') {
	Object.defineProperty(crypto.subtle, 'timingSafeEqual', {
		value(left, right) {
			const bytes = (value) => (
				ArrayBuffer.isView(value)
					? Buffer.from(value.buffer, value.byteOffset, value.byteLength)
					: Buffer.from(value)
			);
			return timingSafeEqual(bytes(left), bytes(right));
		},
	});
}

register('./cf-loader.mjs', import.meta.url);
