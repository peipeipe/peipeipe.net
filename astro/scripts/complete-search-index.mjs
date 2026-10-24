import fs from "node:fs/promises";
import path from "node:path";
import fg from "fast-glob";

// Index rendered public pages so their searchable text follows the actual page content.
export async function completeSearchIndex(distDir) {
  const searchPath = path.join(distDir, "search/index.html");
  const html = await fs.readFile(searchPath, "utf8");
  const dataPattern = /(<script\b[^>]*\bid="search-data"[^>]*>)([\s\S]*?)(<\/script>)/;
  const match = html.match(dataPattern);
  if (!match) throw new Error("Search index is missing from the built search page");
  const index = JSON.parse(match[2]);
  const covered = new Set(index.items.map((item) => decodeURI(new URL(item.url, "https://www.peipeipe.net").pathname)));
  // These pages duplicate entries or are operational pages, rather than public content.
  const excluded = new Set(["/", "/diary/", "/diary-reader/", "/search/", "/404/", "/cloudflare-preview/", "/blog-post/", "/diary-post/"]);
  for (const file of (await fg("**/*.html", { cwd: distDir })).sort()) {
    const url = `/${file.replace(/index\.html$/, "").replace(/\.html$/, "/")}`;
    if (covered.has(url) || excluded.has(url)) continue;
    const page = await fs.readFile(path.join(distDir, file), "utf8");
    if (/<meta\b[^>]*http-equiv="refresh"/i.test(page)) continue;
    if (/<meta\b[^>]*name="robots"[^>]*content="[^"]*noindex/i.test(page)) continue;
    const main = page.match(/<main\b[^>]*>([\s\S]*?)<\/main>/i)?.[1];
    if (!main) continue;
    const plainText = toText(main);
    const title = toText(main.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i)?.[1] || page.match(/<title>([\s\S]*?)<\/title>/i)?.[1] || url);
    const pageTitle = url === "/about/" ? "About" : title;
    index.items.push({ kind: "page", title: pageTitle, url, date: "", excerpt: plainText.slice(0, 200), plainText });
  }
  index.stats.total = index.items.length;
  index.stats.pages = index.items.filter((item) => item.kind === "page").length;
  const serialized = JSON.stringify(index).replace(/</g, "\\u003c");
  await fs.writeFile(searchPath, html.replace(dataPattern, (_, open, data, close) => open + serialized + close));
  console.log(`Search index: ${index.stats.total} items including ${index.stats.pages} public pages`);
}

function toText(html) {
  return html
    .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&#(x[\da-f]+|\d+);/gi, (_, code) => String.fromCodePoint(code[0].toLowerCase() === "x" ? parseInt(code.slice(1), 16) : Number(code)))
    .replace(/&(nbsp|amp|lt|gt|quot|apos);/g, (_, name) => ({ nbsp: " ", amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" })[name])
    .replace(/\s+/g, " ").trim();
}
