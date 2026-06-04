import fs from "node:fs/promises";
import path from "node:path";
import { getPosts } from "../src/lib/content.ts";

const outDir = path.resolve("migration");
await fs.mkdir(outDir, { recursive: true });

const posts = await getPosts();
const invalidPercentUrls = posts
  .filter((post) => post.url.includes("%25"))
  .map((post) => ({
    sourcePath: post.sourcePath,
    title: post.title,
    astroUrl: post.url,
  }));

await fs.writeFile(
  path.join(outDir, "legacy-invalid-percent-slugs.json"),
  `${JSON.stringify(invalidPercentUrls, null, 2)}\n`,
);

console.log(`Found ${invalidPercentUrls.length} legacy invalid percent slug(s).`);
console.log("Wrote migration/legacy-invalid-percent-slugs.json");
