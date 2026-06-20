import booksData from "../../data/books.json";

export const AMAZON_PARTNER_TAG = "peipeipe-22";

export interface BookQuote {
  text: string;
  confidence: "high" | "medium";
  reason: string;
}

export interface Book {
  id: string;
  asin: string;
  amazonUrl: string;
  coverUrl: string;
  isbn13: string;
  format: string;
  rating: number | null;
  status: string;
  tags: string[];
  registeredAt: string;
  readDate: string;
  title: string;
  author: string;
  publisher: string;
  publishedYear: string;
  media: string;
  pages: number | null;
  quotes: BookQuote[];
  droppedPersonalNoteCount: number;
}

export interface BooksData {
  source: string;
  generatedFrom: string;
  stats: {
    books: number;
    withNotes: number;
    withQuotes: number;
    quotes: number;
    personalNotesDropped: number;
  };
  books: Book[];
}

export function amazonAffiliateUrl(asin: string): string {
  if (!/^[0-9A-Z]{10}$/.test(asin)) return "";

  const url = new URL(`https://www.amazon.co.jp/dp/${asin}`);
  url.searchParams.set("tag", AMAZON_PARTNER_TAG);
  return url.toString();
}

export function getBooksData(): BooksData {
  const data = booksData as BooksData;

  return {
    ...data,
    books: data.books.map((book) => ({
      ...book,
      amazonUrl: amazonAffiliateUrl(book.asin),
    })),
  };
}
