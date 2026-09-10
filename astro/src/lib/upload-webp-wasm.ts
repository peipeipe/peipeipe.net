import encode, { init } from '@jsquash/webp/encode.js';
import wasmUrl from '@jsquash/webp/codec/enc/webp_enc.wasm?url';
import simdWasmUrl from '@jsquash/webp/codec/enc/webp_enc_simd.wasm?url';

let ready: Promise<unknown> | undefined;

export async function encodeWebp(pixels: ImageData) {
  ready ??= init({
    locateFile: (path: string) => path.endsWith('webp_enc_simd.wasm') ? simdWasmUrl : wasmUrl,
  }).catch((error: unknown) => {
    ready = undefined;
    throw error;
  });
  await ready;
  return encode(pixels, { quality: 85 });
}
