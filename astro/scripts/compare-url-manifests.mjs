import fs from "node:fs/promises";
import path from "node:path";

const args = new Set(process.argv.slice(2));
const failOnDiff = args.has("--fail-on-diff");
const outDir = path.resolve("migration");
const jekyllPath = path.join(outDir, "jekyll-url-manifest.json");
const astroPath = path.join(outDir, "astro-url-manifest.json");
const outputPath = path.join(outDir, "url-comparison.json");

try {
  const [jekyllManifest, astroManifest] = await Promise.all([
    readManifest(jekyllPath, "PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run manifest:jekyll"),
    readManifest(astroPath, "PATH=/home/peipeipe/.local/nodejs/current/bin:$PATH npm run manifest"),
  ]);

  const jekyllUrls = new Set(jekyllManifest.urls);
  const astroUrls = new Set(astroManifest.urls);
  const missingInAstro = [...jekyllUrls]
    .filter((url) => !astroUrls.has(url))
    .sort((a, b) => a.localeCompare(b, "ja"));
  const extraInAstro = [...astroUrls]
    .filter((url) => !jekyllUrls.has(url))
    .sort((a, b) => a.localeCompare(b, "ja"));

  const comparison = {
    generatedAt: new Date().toISOString(),
    counts: {
      jekyll: jekyllManifest.urls.length,
      astro: astroManifest.urls.length,
      missingInAstro: missingInAstro.length,
      extraInAstro: extraInAstro.length,
    },
    missingInAstro,
    extraInAstro,
  };

  await fs.writeFile(outputPath, `${JSON.stringify(comparison, null, 2)}\n`);

  console.log(`Jekyll URLs: ${comparison.counts.jekyll}`);
  console.log(`Astro URLs: ${comparison.counts.astro}`);
  console.log(`Missing in Astro: ${comparison.counts.missingInAstro}`);
  console.log(`Extra in Astro: ${comparison.counts.extraInAstro}`);
  console.log("Wrote migration/url-comparison.json");

  if (failOnDiff && (missingInAstro.length > 0 || extraInAstro.length > 0)) {
    process.exitCode = 1;
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}

async function readManifest(file, command) {
  let raw;
  try {
    raw = await fs.readFile(file, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") {
      throw new Error(
        `${path.relative(process.cwd(), file)} does not exist. Run "${command}" first.`,
      );
    }
    throw error;
  }

  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed.urls)) {
    throw new Error(`${file} does not contain a urls array.`);
  }
  return parsed;
}
