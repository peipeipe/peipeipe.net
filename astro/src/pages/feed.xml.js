import { getPosts } from "@/lib/content";

export async function GET() {
  const posts = (await getPosts()).slice(0, 20);
  const items = posts.map((post) => `
    <item>
      <title>${escapeXml(post.title)}</title>
      <link>https://www.peipeipe.net${post.url}</link>
      <guid>https://www.peipeipe.net${post.url}</guid>
      <pubDate>${post.date.toUTCString()}</pubDate>
      <description>${escapeXml(post.excerpt)}</description>
    </item>
  `).join("");

  return new Response(`<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>peipeipe.net - 読んだ本とやったこと</title>
    <link>https://www.peipeipe.net/</link>
    <description>読んだ本とやったこと</description>
    ${items}
  </channel>
</rss>
`, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
    },
  });
}

function escapeXml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
