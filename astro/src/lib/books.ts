import booksData from "../../data/books.json";

export interface BookQuote {
  text: string;
  confidence: "high" | "medium";
  reason: string;
}

export interface Book {
  id: string;
  asin: string;
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

export function getBooksData(): BooksData {
  return booksData as BooksData;
}

export function getBooks(): Book[] {
  return getBooksData().books;
}

export function bookUrl(book: Book): string {
  return `/books/#${book.id}`;
}

export function bookPlainText(book: Book): string {
  return [
    book.title,
    book.author,
    book.publisher,
    book.publishedYear,
    book.readDate,
    book.tags.join(" "),
    book.quotes.map((quote) => quote.text).join(" "),
  ].filter(Boolean).join(" ");
}
