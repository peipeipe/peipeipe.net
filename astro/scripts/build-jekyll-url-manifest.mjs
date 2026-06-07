import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve("..");
const siteDir = path.join(repoRoot, "_site");
const outDir = path.resolve("migration");
const routeExtensions = new Set([".html", ".json", ".txt", ".xml"]);

await assertDirectory(siteDir);
await fs.mkdir(outDir, { recursive: true });

const files = await listFiles(siteDir);

const urls = files
  .filter((file) => routeExtensions.has(path.extname(file)))
  .map(fileToUrl)
  .sort((a, b) => a.localeCompare(b, "ja"));

const manifest = {
  generatedAt: new Date().toISOString(),
  source: "_site",
  counts: {
    urls: urls.length,
  },
  urls,
};

await fs.writeFile(
  path.join(outDir, "jekyll-url-manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
);

console.log(`Wrote ${urls.length} URLs to migration/jekyll-url-manifest.json`);

function fileToUrl(file) {
  const normalized = file.split(path.sep).join("/");
  if (normalized.endsWith("/index.html")) {
    return `/${normalized.slice(0, -"index.html".length)}`;
  }
  if (normalized === "index.html") {
    return "/";
  }
  if (normalized.endsWith(".html") && normalized !== "404.html") {
    return `/${normalized.slice(0, -".html".length)}`;
  }
  return `/${normalized}`;
}

async function assertDirectory(directory) {
  try {
    const stat = await fs.stat(directory);
    if (stat.isDirectory()) return;
  } catch {
    // Fall through to the explicit error below.
  }

  throw new Error(
    `${directory} does not exist. Run "bundle exec jekyll build" from the repository root first.`,
  );
}

async function listFiles(directory, prefix = "") {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const files = await Promise.all(entries.map(async (entry) => {
    const relativePath = path.join(prefix, entry.name);
    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return listFiles(absolutePath, relativePath);
    }
    if (entry.isFile()) {
      return [relativePath];
    }
    return [];
  }));

  return files.flat();
}
