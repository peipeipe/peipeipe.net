import fs from "node:fs/promises";
import path from "node:path";
import { getDiaryEntries, getPosts } from "../src/lib/content.ts";

const outDir = path.resolve("migration");
await fs.mkdir(outDir, { recursive: true });

const posts = await getPosts();
const diary = await getDiaryEntries();
const urls = [
  "/",
  "/.well-known/nostr.json",
  "/404.html",
  "/activity/",
  "/activity-data.json",
  "/about",
  "/cloudflare-preview/",
  "/blog-post/",
  "/diary/",
  "/diary-post/",
  "/feed.xml",
  "/mountains/",
  "/mountains-data.json",
  "/places/",
  "/places-data.json",
  "/places.json",
  "/robots.txt",
  "/search",
  "/sitemap-index.xml",
  ...posts.map((post) => post.url),
  ...diary.map((entry) => entry.url),
].sort((a, b) => a.localeCompare(b, "ja"));

const manifest = {
  generatedAt: new Date().toISOString(),
  counts: {
    posts: posts.length,
    diary: diary.length,
    urls: urls.length,
  },
  urls,
};

await fs.writeFile(
  path.join(outDir, "astro-url-manifest.json"),
  `${JSON.stringify(manifest, null, 2)}\n`,
);

console.log(`Wrote ${urls.length} URLs to migration/astro-url-manifest.json`);
