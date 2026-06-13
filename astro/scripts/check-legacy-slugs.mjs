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

const legacyUrlIssues = posts.flatMap((post) => {
  const issues = [];
  const sourceSlug = slugFromSourcePath(post.sourcePath);
  const permalink = typeof post.data.permalink === "string" ? post.data.permalink : "";

  if (sourceSlug !== sourceSlug.trim()) {
    issues.push({
      kind: "post",
      issue: "filename-slug-has-outer-whitespace",
      sourcePath: post.sourcePath,
      title: post.title,
      astroUrl: post.url,
    });
  }

  if (sourceSlug.includes(" copy")) {
    issues.push({
      kind: "post",
      issue: "filename-slug-has-copy-suffix",
      sourcePath: post.sourcePath,
      title: post.title,
      astroUrl: post.url,
    });
  }

  if (/\s/.test(permalink)) {
    issues.push({
      kind: "post",
      issue: "permalink-contains-whitespace",
      sourcePath: post.sourcePath,
      title: post.title,
      astroUrl: post.url,
    });
  }

  return issues;
});

await fs.writeFile(
  path.join(outDir, "legacy-invalid-percent-slugs.json"),
  `${JSON.stringify(invalidPercentUrls, null, 2)}\n`,
);

await fs.writeFile(
  path.join(outDir, "legacy-url-issues.json"),
  `${JSON.stringify(legacyUrlIssues, null, 2)}\n`,
);

console.log(`Found ${invalidPercentUrls.length} legacy invalid percent slug(s).`);
console.log("Wrote migration/legacy-invalid-percent-slugs.json");
console.log(`Found ${legacyUrlIssues.length} legacy URL issue(s).`);
console.log("Wrote migration/legacy-url-issues.json");

function slugFromSourcePath(sourcePath) {
  const filename = path.basename(sourcePath, ".md");
  const match = filename.match(/^\d{4}-\d{1,2}-\d{1,2}-(.+)$/);
  return match?.[1] ?? filename;
}
