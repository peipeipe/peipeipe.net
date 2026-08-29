import fs from "node:fs/promises";
import path from "node:path";

const publicDir = path.resolve("public");
const distDir = path.resolve("dist");

await copyIfExists(path.join(publicDir, ".well-known", "nostr.json"), path.join(distDir, "nostr.json"));
await copyMapLibreAssets();
await writeRedirects();

console.log("Finalized public assets in dist/");

async function copyIfExists(from, to) {
  try {
    await fs.cp(from, to, { recursive: true, force: true });
  } catch (error) {
    if (error?.code === "ENOENT") return;
    throw error;
  }
}

async function writeRedirects() {
  const redirectsPath = path.join(distDir, "_redirects");
  const redirects = [
    "/.well-known/nostr.json /nostr.json 200",
  ];

  await fs.writeFile(redirectsPath, `${redirects.join("\n")}\n`);
}

async function copyMapLibreAssets() {
  const mapLibreDistDir = path.resolve("node_modules", "maplibre-gl", "dist");
  const assetsDir = path.join(distDir, "_astro");
  const assets = ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"];

  await fs.mkdir(assetsDir, { recursive: true });
  await Promise.all(
    assets.map((asset) => fs.copyFile(path.join(mapLibreDistDir, asset), path.join(assetsDir, asset))),
  );
}
