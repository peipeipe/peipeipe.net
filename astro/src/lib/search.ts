import { getDiaryEntries, getPosts, formatEntryDate } from "@/lib/content";

export type SearchKind = "all" | "post" | "diary";

export interface SearchItem {
  kind: Exclude<SearchKind, "all">;
  title: string;
  url: string;
  date: string;
  excerpt: string;
  plainText: string;
  imageSrc?: string;
}

export interface SearchIndex {
  generatedAt: string;
  stats: {
    posts: number;
    diary: number;
    total: number;
  };
  items: SearchItem[];
}

export async function buildSearchIndex(): Promise<SearchIndex> {
  const [posts, diaryEntries] = await Promise.all([getPosts(), getDiaryEntries()]);

  const items = [
    ...posts.map((entry) => ({
      kind: "post" as const,
      title: entry.title,
      url: entry.url,
      date: formatEntryDate(entry.date),
      excerpt: entry.excerpt,
      plainText: htmlToPlainText(entry.html),
      imageSrc: getFirstImageSrc(entry.html),
    })),
    ...diaryEntries.map((entry) => ({
      kind: "diary" as const,
      title: entry.title,
      url: entry.url,
      date: formatEntryDate(entry.date),
      excerpt: entry.excerpt,
      plainText: htmlToPlainText(entry.html),
      imageSrc: getFirstImageSrc(entry.html),
    })),
  ].sort((a, b) => b.date.localeCompare(a.date));

  return {
    generatedAt: new Date().toISOString(),
    stats: {
      posts: posts.length,
      diary: diaryEntries.length,
      total: items.length,
    },
    items,
  };
}

function getFirstImageSrc(html: string): string | undefined {
  return html.match(/<img\s[^>]*src="([^"]+)"/)?.[1];
}

function htmlToPlainText(html: string): string {
  return html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}
