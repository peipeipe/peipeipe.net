/** Encode once from canvas pixels; never transcode a lossy JPEG fallback. */
export async function writeWebpBlob(canvas: HTMLCanvasElement) {
  const mime = 'image/webp';
  const nativeBlob = await new Promise<Blob | null>((resolve) => {
    try {
      canvas.toBlob(resolve, mime, 0.85);
    } catch {
      resolve(null);
    }
  });
  if (nativeBlob?.type === mime) return { blob: nativeBlob, mime };

  const context = canvas.getContext('2d');
  if (!context) throw new Error('画像を処理できませんでした');
  const { encodeWebp } = await import('./upload-webp-wasm');
  const bytes = await encodeWebp(context.getImageData(0, 0, canvas.width, canvas.height));
  return { blob: new Blob([bytes], { type: mime }), mime };
}
