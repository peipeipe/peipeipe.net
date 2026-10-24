import { getDiaryEntries, getPosts, formatEntryDate } from "@/lib/content";
import { getActivities, formatDistance, formatDuration } from "@/lib/activity";
import { getBooksData } from "@/lib/books";
import { getOnsenPlaces } from "@/lib/checkins";
import { getCompositionMap } from "@/lib/composition";

export type SearchKind = "all" | "post" | "diary" | "onsen" | "book" | "page";

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
    books: number;
    posts: number;
    diary: number;
    onsen: number;
    total: number;
  };
  items: SearchItem[];
}

export async function buildSearchIndex(): Promise<SearchIndex> {
  const [posts, diaryEntries] = await Promise.all([getPosts(), getDiaryEntries()]);
  const { books } = getBooksData();
  const onsenPlaces = getOnsenPlaces();
  const compositionMap = getCompositionMap();

  const items: SearchItem[] = [
    {
      kind: "page",
      title: "アクティビティマップ",
      url: "/activity/",
      date: "",
      excerpt: "Strava に記録した走行・ライドの軌跡、走破マップ・ヒートマップ",
      plainText: getActivities().map((activity) => [activity.name, activity.sport_type,
        activity.start_date, formatDistance(activity.distance), formatDuration(activity.moving_time),
        `${activity.total_elevation_gain}m up`].join(" ")).join(" "),
    },
    ...books.map((book) => ({
      kind: "book" as const,
      title: book.title,
      url: `/books/?book=${encodeURIComponent(book.id)}#${encodeURIComponent(book.id)}`,
      date: book.readDate || book.registeredAt || "",
      excerpt: [book.author, book.publisher, book.publishedYear, book.quotes[0]?.text].filter(Boolean).join(" / ").slice(0, 240),
      plainText: ["本 読書 Books", book.title, book.author, book.publisher, book.publishedYear,
        book.readDate, book.format, book.status, ...book.tags, ...book.quotes.map((quote) => quote.text)].filter(Boolean).join(" "),
    })),
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
    ...onsenPlaces.map((place) => {
      const springs = compositionMap.get(place.fsq_id || "") || [];
      const excerpt = [place.address, place.user_comment].filter(Boolean).join(" / ");
      return {
        kind: "onsen" as const,
        title: place.name,
        url: `/onsen/?q=${encodeURIComponent(place.name)}`,
        date: place.date || "",
        excerpt,
        plainText: [
          "温泉 サウナ Onsen",
          place.name,
          excerpt,
          ...(place.categories || []),
          ...springs.flatMap((spring) => [
            spring.spring_name, spring.spring_quality, spring.spring_quality_class,
            spring.notes, spring.analyzer, ...(spring.indications || []), ...(spring.contraindications || []),
            ...[...(spring.cations || []), ...(spring.anions || []), ...(spring.undissociated || []),
              ...(spring.dissolved_gas || [])].flatMap((ingredient) => [ingredient.name, ingredient.symbol]),
          ]),
        ].filter(Boolean).join(" "),
      };
    }),
  ].sort((a, b) => b.date.localeCompare(a.date));

  return {
    generatedAt: new Date().toISOString(),
    stats: {
      books: books.length,
      posts: posts.length,
      diary: diaryEntries.length,
      onsen: onsenPlaces.length,
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
