import fs from "node:fs/promises";
import path from "node:path";
import fg from "fast-glob";
import matter from "gray-matter";
import { marked } from "marked";

const repoRoot = path.resolve("..");

type Frontmatter = Record<string, unknown>;

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
  const files = await fg("_posts/*.md", { cwd: repoRoot, absolute: true });
  const posts = await Promise.all(files.map((file) => readEntry(file, "post")));
  return posts.sort((a, b) => b.date.getTime() - a.date.getTime());
}

export async function getDiaryEntries(): Promise<Entry[]> {
  const files = await fg("_diary/*.md", { cwd: repoRoot, absolute: true });
  const entries = await Promise.all(files.map((file) => readEntry(file, "diary")));
  return entries.sort((a, b) => b.date.getTime() - a.date.getTime());
}

async function readEntry(file: string, kind: "post" | "diary"): Promise<Entry> {
  const raw = await fs.readFile(file, "utf8");
  const parsed = matter(raw);
  const filename = path.basename(file, ".md");
  const fileDate = dateFromFilename(filename);
  const date = parseDate(parsed.data.date) || fileDate || new Date(0);
  const title = String(parsed.data.title || titleFromFilename(filename) || filename);
  const content = normalizeMarkdownImageUrls(parsed.content);
  const html = await marked.parse(content, { async: true, gfm: true });
  const excerpt = makeExcerpt(html);
  const url = kind === "diary"
    ? diaryUrl(date)
    : postUrl(filename, parsed.data, date);

  return {
    sourcePath: path.relative(repoRoot, file),
    title,
    date,
    url,
    excerpt,
    html,
    data: parsed.data,
  };
}

function postUrl(filename: string, data: Frontmatter, date: Date): string {
  const slug = safeUrlSlug(titleFromFilename(filename) || filename);
  const permalink = typeof data.permalink === "string" ? data.permalink : "/:title/";
  const replaced = permalink
    .replace(":year", String(date.getFullYear()))
    .replace(":month", pad2(date.getMonth() + 1))
    .replace(":day", pad2(date.getDate()))
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
  return normalizeUrl(`/diary/${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}/`);
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
  return match?.[1];
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

function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
