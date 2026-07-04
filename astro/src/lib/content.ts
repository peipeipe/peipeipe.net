import fs from "node:fs/promises";
import path from "node:path";
import fg from "fast-glob";
import { load as parseYaml } from "js-yaml";
import { marked } from "marked";

const astroRoot = path.resolve(".");
const contentRoot = path.join(astroRoot, "content");

type Frontmatter = Record<string, unknown>;

interface LinkCardMetadata {
  url: string;
  title: string;
  description: string;
  image: string;
  siteName: string;
  host: string;
}

interface LinkCardCandidate {
  url: string;
  fallbackTitle: string;
}

const linkCardCache = new Map<string, LinkCardMetadata | undefined>();

export interface Entry {
  sourcePath: string;
  title: string;
  date: Date;
  url: string;
  excerpt: string;
  html: string;
  data: Frontmatter;
}

marked.use({
  renderer: {
    link({ href, title, tokens }) {
      const text = this.parser.parseInline(tokens);
      const titleAttr = title ? ` title="${escapeHtml(title)}"` : "";
      const externalAttrs = href?.startsWith("http") ? ' target="_blank" rel="noopener noreferrer"' : "";
      return `<a href="${escapeHtml(href || "")}"${titleAttr}${externalAttrs}>${text}</a>`;
    },
  },
});

export async function getPosts(): Promise<Entry[]> {
  const files = await fg("posts/*.md", { cwd: contentRoot, absolute: true });
  const posts = await Promise.all(files.map((file) => readEntry(file, "post")));
  return posts.sort((a, b) => b.date.getTime() - a.date.getTime());
}

export async function getDiaryEntries(): Promise<Entry[]> {
  const files = await fg("diary/*.md", { cwd: contentRoot, absolute: true });
  const entries = await Promise.all(files.map((file) => readEntry(file, "diary")));
  return entries.sort((a, b) => b.date.getTime() - a.date.getTime());
}

async function readEntry(file: string, kind: "post" | "diary"): Promise<Entry> {
  const raw = await fs.readFile(file, "utf8");
  const parsed = parseFrontmatter(raw);
  const filename = path.basename(file, ".md");
  const fileDate = dateFromFilename(filename);
  const date = parseDate(parsed.data.date) || fileDate || new Date(0);
  const title = String(parsed.data.title || titleFromFilename(filename) || filename);
  const content = await renderStandaloneLinkCards(normalizeMarkdownImageUrls(parsed.content), kind);
  const html = await marked.parse(content, { async: true, gfm: true, breaks: kind === "diary" });
  const excerpt = makeExcerpt(html);
  const url = kind === "diary"
    ? diaryUrl(date)
    : postUrl(filename, parsed.data, date);

  return {
    sourcePath: path.relative(astroRoot, file),
    title,
    date,
    url,
    excerpt,
    html,
    data: parsed.data,
  };
}

function parseFrontmatter(raw: string): { data: Frontmatter; content: string } {
  const normalized = raw.replace(/\r\n/g, "\n");
  const match = normalized.match(/^---\n([\s\S]*?)\n---(?:\n|$)([\s\S]*)$/);
  if (!match) {
    return { data: {}, content: raw };
  }

  const [, frontmatter, content] = match;
  const data = parseYaml(frontmatter);

  return {
    data: isFrontmatter(data) ? data : {},
    content,
  };
}

function isFrontmatter(value: unknown): value is Frontmatter {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function postUrl(filename: string, data: Frontmatter, date: Date): string {
  const slug = safeUrlSlug(titleFromFilename(filename) || filename);
  const parts = datePartsInTokyo(date);
  const permalink = typeof data.permalink === "string" ? data.permalink : "/:title/";
  const replaced = permalink
    .replace(":year", parts.year)
    .replace(":month", parts.month)
    .replace(":day", parts.day)
    .replace(":title", slug);

  return normalizeUrl(replaced);
}

function safeUrlSlug(slug: string): string {
  try {
    decodeURI(slug);
    return slug;
  } catch {
    return slug.replace(/%/g, "%2525");
  }
}

function diaryUrl(date: Date): string {
  return normalizeUrl(`/diary/${formatEntryDate(date)}/`);
}

export function formatEntryDate(date: Date): string {
  const parts = datePartsInTokyo(date);
  return `${parts.year}-${parts.month}-${parts.day}`;
}

function normalizeUrl(value: string): string {
  const withoutDuplicateSlash = value.replace(/\/+/g, "/");
  const withLeadingSlash = withoutDuplicateSlash.startsWith("/") ? withoutDuplicateSlash : `/${withoutDuplicateSlash}`;
  return withLeadingSlash.endsWith("/") ? withLeadingSlash : `${withLeadingSlash}/`;
}

function dateFromFilename(filename: string): Date | undefined {
  const match = filename.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (!match) return undefined;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

function titleFromFilename(filename: string): string | undefined {
  const match = filename.match(/^\d{4}-\d{1,2}-\d{1,2}-(.+)$/);
  return match?.[1]?.trim();
}

function parseDate(value: unknown): Date | undefined {
  if (value instanceof Date) return value;
  if (typeof value !== "string" && typeof value !== "number") return undefined;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

function makeExcerpt(html: string): string {
  const text = html
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .trim();

  const firstSentence = text.match(/^.+?[。！？.!?](?:[」』）)]*)/)?.[0];
  return (firstSentence || text.slice(0, 120)).trim();
}

function normalizeMarkdownImageUrls(content: string): string {
  return content.replace(/!\[([^\]]*)\]\(([^)\n]+)\)/g, (match, alt: string, destination: string) => {
    const trimmed = destination.trim();
    if (!/\s/.test(trimmed) || !/^(https?:\/\/|\/)/.test(trimmed)) return match;
    return `![${alt}](${trimmed.replace(/\s+/g, "%20")})`;
  });
}

async function renderStandaloneLinkCards(content: string, kind: "post" | "diary"): Promise<string> {
  const lines = content.split("\n");
  const rendered = await Promise.all(lines.map(async (line) => {
    const candidate = linkCardCandidate(line);
    if (!candidate) return line;
    if (kind === "post" && isAmazonUrl(candidate.url)) return renderAmazonLinkCard(candidate);
    if (!shouldRenderLinkCard(candidate.url)) return line;

    const metadata = await getLinkCardMetadata(candidate.url);
    return renderLinkCard(metadata || fallbackLinkCardMetadata(candidate));
  }));

  return rendered.join("\n");
}

function linkCardCandidate(line: string): LinkCardCandidate | undefined {
  const trimmed = line.trim();
  if (trimmed.startsWith("[") && trimmed.endsWith("]")) return undefined;

  const match = trimmed.match(/^(?:(.*?)\s+)?<?(https?:\/\/\S+?)>?$/);
  if (!match) return undefined;

  try {
    const url = new URL(match[2]).toString();
    if ((trimmed.match(/https?:\/\//g) || []).length > 1) return undefined;
    return {
      url,
      fallbackTitle: match[1]?.trim() || "",
    };
  } catch {
    return undefined;
  }
}

function shouldRenderLinkCard(value: string): boolean {
  const url = new URL(value);
  const hostname = url.hostname.replace(/^www\./, "").toLowerCase();
  return !["x.com", "twitter.com"].includes(hostname);
}

function isAmazonUrl(value: string): boolean {
  const hostname = new URL(value).hostname.replace(/^www\./, "").toLowerCase();
  return hostname === "amzn.to"
    || hostname === "a.co"
    || hostname === "amzn.asia"
    || hostname === "amazon.com"
    || hostname.endsWith(".amazon.com")
    || hostname === "amazon.co.jp"
    || hostname.endsWith(".amazon.co.jp");
}

async function getLinkCardMetadata(url: string): Promise<LinkCardMetadata | undefined> {
  if (linkCardCache.has(url)) return linkCardCache.get(url);

  const metadata = await fetchLinkCardMetadata(url).catch(() => undefined);
  linkCardCache.set(url, metadata);
  return metadata;
}

async function fetchLinkCardMetadata(url: string): Promise<LinkCardMetadata | undefined> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2500);

  try {
    const response = await fetch(url, {
      headers: {
        "accept": "text/html,application/xhtml+xml",
        "user-agent": "peipeipe.net link-card fetcher",
      },
      redirect: "follow",
      signal: controller.signal,
    });

    if (!response.ok) return undefined;

    const contentType = response.headers.get("content-type") || "";
    if (contentType && !/text\/html|application\/xhtml\+xml/i.test(contentType)) return undefined;

    const contentLength = Number(response.headers.get("content-length") || 0);
    if (contentLength > 2_000_000) return undefined;

    const html = await response.text();
    const finalUrl = response.url || url;
    const title = firstMeta(html, [
      ['meta[property="og:title"]', "content"],
      ['meta[name="twitter:title"]', "content"],
      ["title", "text"],
    ]);
    const description = firstMeta(html, [
      ['meta[property="og:description"]', "content"],
      ['meta[name="description"]', "content"],
      ['meta[name="twitter:description"]', "content"],
    ]);
    const image = firstMeta(html, [
      ['meta[property="og:image"]', "content"],
      ['meta[name="twitter:image"]', "content"],
    ]);
    const siteName = firstMeta(html, [
      ['meta[property="og:site_name"]', "content"],
      ['meta[name="application-name"]', "content"],
    ]);
    const host = new URL(finalUrl).hostname.replace(/^www\./, "");

    return {
      url: finalUrl,
      title: title || host,
      description,
      image: image ? new URL(image, finalUrl).toString() : "",
      siteName,
      host,
    };
  } finally {
    clearTimeout(timeout);
  }
}

function fallbackLinkCardMetadata(candidate: LinkCardCandidate): LinkCardMetadata {
  const url = new URL(candidate.url);
  const host = url.hostname.replace(/^www\./, "");

  return {
    url: candidate.url,
    title: candidate.fallbackTitle || host,
    description: "",
    image: "",
    siteName: "",
    host,
  };
}

function firstMeta(html: string, selectors: Array<[string, "content" | "text"]>): string {
  for (const [selector, source] of selectors) {
    const value = source === "text" ? matchTitle(html) : matchMetaContent(html, selector);
    if (value) return normalizeMetaValue(value);
  }
  return "";
}

function matchTitle(html: string): string {
  return html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] || "";
}

function matchMetaContent(html: string, selector: string): string {
  const attrMatch = selector.match(/^meta\[(name|property)="([^"]+)"\]$/);
  if (!attrMatch) return "";

  const [, attrName, attrValue] = attrMatch;
  const tagPattern = new RegExp(`<meta\\b(?=[^>]*\\b${attrName}=["']${escapeRegExp(attrValue)}["'])(?=[^>]*\\bcontent=["']([^"']*)["'])[^>]*>`, "i");
  return html.match(tagPattern)?.[1] || "";
}

function normalizeMetaValue(value: string): string {
  return decodeHtmlEntities(value)
    .replace(/\s+/g, " ")
    .trim();
}

function decodeHtmlEntities(value: string): string {
  return value
    .replace(/&#(\d+);/g, (_match, code) => String.fromCodePoint(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_match, code) => String.fromCodePoint(Number.parseInt(code, 16)))
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

function renderLinkCard(metadata: LinkCardMetadata): string {
  const media = metadata.image
    ? `<span class="link-card-media"><img src="${escapeHtml(metadata.image)}" alt="" loading="lazy"></span>`
    : "";
  const description = metadata.description
    ? `<span class="link-card-description">${escapeHtml(metadata.description)}</span>`
    : "";
  const source = metadata.siteName || metadata.host;

  return `<a class="link-card" href="${escapeHtml(metadata.url)}" target="_blank" rel="noopener noreferrer">${media}<span class="link-card-body"><span class="link-card-title">${escapeHtml(metadata.title)}</span>${description}<span class="link-card-source">${escapeHtml(source)}</span></span></a>`;
}

function renderAmazonLinkCard(candidate: LinkCardCandidate): string {
  const title = candidate.fallbackTitle || "Amazon.co.jpで詳細を見る";
  const host = new URL(candidate.url).hostname.replace(/^www\./, "");

  return `<a class="amazon-link-card" href="${escapeHtml(candidate.url)}" target="_blank" rel="nofollow noopener noreferrer"><span class="amazon-link-card-badge">Amazon</span><span class="amazon-link-card-body"><span class="amazon-link-card-title">${escapeHtml(title)}</span><span class="amazon-link-card-source">${escapeHtml(host)}</span></span></a>`;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

export function datePartsInTokyo(date: Date) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return {
    year: values.year,
    month: values.month,
    day: values.day,
    hour: values.hour,
    minute: values.minute,
  };
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
