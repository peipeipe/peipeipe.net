import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

const excludedSitemapPaths = new Set([
  "/books/",
  "/books/review/",
  "/cloudflare-preview/",
  "/diary-post/",
  "/search/",
]);

export default defineConfig({
  site: "https://www.peipeipe.net",
  output: "static",
  integrations: [
    sitemap({
      filter: (url) => !excludedSitemapPaths.has(new URL(url).pathname),
    }),
  ],
});
