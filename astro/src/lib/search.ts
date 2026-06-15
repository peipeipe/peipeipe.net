import { getDiaryEntries, getPosts, formatEntryDate } from "@/lib/content";
import { bookPlainText, bookUrl, getBooks } from "@/lib/books";

export type SearchKind = "all" | "post" | "diary" | "book";

export interface SearchItem {
  kind: Exclude<SearchKind, "all">;
  title: string;
  url: string;
  date: string;
  excerpt: string;
  plainText: string;
}

export interface SearchIndex {
  generatedAt: string;
  stats: {
    posts: number;
    diary: number;
    books: number;
    total: number;
  };
  items: SearchItem[];
}

export async function buildSearchIndex(): Promise<SearchIndex> {
  const [posts, diaryEntries] = await Promise.all([getPosts(), getDiaryEntries()]);
  const books = getBooks();

  const items = [
    ...posts.map((entry) => ({
      kind: "post" as const,
      title: entry.title,
      url: entry.url,
      date: formatEntryDate(entry.date),
      excerpt: entry.excerpt,
      plainText: htmlToPlainText(entry.html),
    })),
    ...diaryEntries.map((entry) => ({
      kind: "diary" as const,
      title: entry.title,
      url: entry.url,
      date: formatEntryDate(entry.date),
      excerpt: entry.excerpt,
      plainText: htmlToPlainText(entry.html),
    })),
    ...books.map((book) => {
      const plainText = bookPlainText(book);
      const firstQuote = book.quotes[0]?.text || "";
      return {
        kind: "book" as const,
        title: book.title,
        url: bookUrl(book),
        date: book.readDate || book.registeredAt || "0000-00-00",
        excerpt: firstQuote || [book.author, book.publisher, book.publishedYear].filter(Boolean).join(" / "),
        plainText,
      };
    }),
  ].sort((a, b) => b.date.localeCompare(a.date));

  return {
    generatedAt: new Date().toISOString(),
    stats: {
      posts: posts.length,
      diary: diaryEntries.length,
      books: books.length,
      total: items.length,
    },
    items,
  };
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
