import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

export default defineConfig({
  site: "https://www.peipeipe.net",
  output: "static",
  integrations: [sitemap()],
});
