import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve("..");
const distDir = path.resolve("dist");

await copyIfExists(path.join(repoRoot, "images"), path.join(distDir, "images"));
await copyIfExists(path.join(repoRoot, ".well-known"), path.join(distDir, ".well-known"));
await copyIfExists(path.join(repoRoot, "favicon.ico"), path.join(distDir, "favicon.ico"));

console.log("Copied root static assets into dist/");

async function copyIfExists(from, to) {
  try {
    await fs.cp(from, to, { recursive: true, force: true });
  } catch (error) {
    if (error?.code === "ENOENT") return;
    throw error;
  }
}
