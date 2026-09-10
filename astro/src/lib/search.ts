import { getDiaryEntries, getPosts, formatEntryDate } from "@/lib/content";
import { getOnsenPlaces } from "@/lib/checkins";
import { getCompositionMap } from "@/lib/composition";

export type SearchKind = "all" | "post" | "diary" | "onsen";

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
    onsen: number;
    total: number;
  };
  items: SearchItem[];
}

export async function buildSearchIndex(): Promise<SearchIndex> {
  const [posts, diaryEntries] = await Promise.all([getPosts(), getDiaryEntries()]);
  const onsenPlaces = getOnsenPlaces();
  const compositionMap = getCompositionMap();

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
          ...springs.flatMap((spring) => [spring.spring_quality, spring.spring_quality_class]),
        ].filter(Boolean).join(" "),
      };
    }),
  ].sort((a, b) => b.date.localeCompare(a.date));

  return {
    generatedAt: new Date().toISOString(),
    stats: {
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
