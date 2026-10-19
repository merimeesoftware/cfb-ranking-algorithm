import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';

function fillRect(png, mask, rgba) {
  const x0 = Math.max(0, mask.x | 0);
  const y0 = Math.max(0, mask.y | 0);
  const x1 = Math.min(png.width, x0 + (mask.width | 0));
  const y1 = Math.min(png.height, y0 + (mask.height | 0));
  for (let y = y0; y < y1; y += 1) {
    for (let x = x0; x < x1; x += 1) {
      const i = (png.width * y + x) << 2;
      png.data[i] = rgba[0];
      png.data[i + 1] = rgba[1];
      png.data[i + 2] = rgba[2];
      png.data[i + 3] = rgba[3];
    }
  }
}

function applyMasks(actual, expected, masks) {
  if (!Array.isArray(masks)) return;
  for (const mask of masks) {
    if (!mask || !Number.isFinite(mask.width) || !Number.isFinite(mask.height)) continue;
    fillRect(actual, mask, [0, 0, 0, 255]);
    fillRect(expected, mask, [0, 0, 0, 255]);
  }
}

function blit(dest, src, offsetX) {
  for (let y = 0; y < src.height; y += 1) {
    for (let x = 0; x < src.width; x += 1) {
      const si = (src.width * y + x) << 2;
      const di = (dest.width * y + (x + offsetX)) << 2;
      dest.data[di] = src.data[si];
      dest.data[di + 1] = src.data[si + 1];
      dest.data[di + 2] = src.data[si + 2];
      dest.data[di + 3] = src.data[si + 3];
    }
  }
}

/**
 * Real image diff. `pass` is returned only when both buffers are the same
 * size and the differing-pixel ratio is within maxDiffRatio.
 */
export function comparePngBuffers(actualBuf, expectedBuf, options = {}) {
  const actual = PNG.sync.read(actualBuf);
  const expected = PNG.sync.read(expectedBuf);
  if (actual.width !== expected.width || actual.height !== expected.height) {
    return {
      status: 'fail',
      reason: 'size mismatch',
      diffPixels: null,
      ratio: null,
      width: actual.width,
      height: actual.height,
      expectedWidth: expected.width,
      expectedHeight: expected.height,
      diffPng: null,
    };
  }
  applyMasks(actual, expected, options.masks);
  const diff = new PNG({ width: actual.width, height: actual.height });
  const diffPixels = pixelmatch(
    actual.data,
    expected.data,
    diff.data,
    actual.width,
    actual.height,
    {
      threshold: options.pixelmatchThreshold,
      includeAA: false,
    }
  );
  const total = actual.width * actual.height;
  const ratio = total === 0 ? 1 : diffPixels / total;
  const status = ratio <= options.maxDiffRatio ? 'pass' : 'fail';
  return {
    status,
    reason: status === 'pass' ? 'within threshold' : 'pixels differ',
    diffPixels,
    ratio,
    width: actual.width,
    height: actual.height,
    diffPng: PNG.sync.write(diff),
  };
}

export function sideBySidePng(expectedBuf, diffBuf, actualBuf) {
  const expected = PNG.sync.read(expectedBuf);
  const diff = PNG.sync.read(diffBuf);
  const actual = PNG.sync.read(actualBuf);
  const out = new PNG({
    width: expected.width + diff.width + actual.width,
    height: Math.max(expected.height, diff.height, actual.height),
  });
  out.data.fill(255);
  blit(out, expected, 0);
  blit(out, diff, expected.width);
  blit(out, actual, expected.width + diff.width);
  return PNG.sync.write(out);
}

/** Solid-color PNG helper used by the planted-fixture self-test. */
export function solidPng(width, height, rgba) {
  const png = new PNG({ width, height });
  for (let i = 0; i < png.data.length; i += 4) {
    png.data[i] = rgba[0];
    png.data[i + 1] = rgba[1];
    png.data[i + 2] = rgba[2];
    png.data[i + 3] = rgba[3];
  }
  return PNG.sync.write(png);
}
