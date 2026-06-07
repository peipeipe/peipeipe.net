import onsenPlaces from "../../../_data/onsen_places.json";
import places from "../../../_data/places.json";

export type CheckinPlace = {
  name: string;
  user_comment?: string;
  date?: string;
  lat?: number | null;
  lng?: number | null;
  address?: string;
  foursquare_url?: string;
  photos?: string[];
  categories?: string[];
  category_group?: string;
  category_label?: string;
  category_emoji?: string;
  category_color?: string;
  data_source?: string;
  fsq_id?: string;
  checkin_count?: number;
  first_checkin_at?: string;
  last_checkin_at?: string;
  updated_at?: string;
};

export function normalizePlace(place: CheckinPlace): Required<Pick<CheckinPlace, "name" | "address">> & CheckinPlace {
  return {
    ...place,
    name: place.name || "",
    address: place.address || "",
    user_comment: place.user_comment || "",
    date: place.date || "",
    lat: Number.isFinite(place.lat) ? place.lat : null,
    lng: Number.isFinite(place.lng) ? place.lng : null,
    photos: place.photos || [],
    categories: place.categories || [],
    category_group: place.category_group || "other",
    category_label: place.category_label || "その他",
    category_emoji: place.category_emoji || "📍",
    category_color: place.category_color || "#607d8b",
    checkin_count: place.checkin_count || 1,
  };
}

export function getPlaces() {
  return (places as CheckinPlace[]).map(normalizePlace);
}

export function getOnsenPlaces() {
  return (onsenPlaces as CheckinPlace[]).map(normalizePlace);
}

export function summarizePlaces(items: CheckinPlace[]) {
  return {
    count: items.length,
    checkins: items.reduce((sum, place) => sum + (Number(place.checkin_count) || 0), 0),
    withPhotos: items.filter((place) => (place.photos || []).length > 0).length,
    latest: items.reduce<CheckinPlace | null>(
      (current, place) => (!current || (place.date || "") > (current.date || "") ? place : current),
      null,
    ),
  };
}

export function categorySummary(items: CheckinPlace[]) {
  const groups = new Map<string, { key: string; label: string; emoji: string; color: string; count: number }>();
  items.forEach((place) => {
    const key = place.category_group || "other";
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        label: place.category_label || "その他",
        emoji: place.category_emoji || "📍",
        color: place.category_color || "#607d8b",
        count: 0,
      });
    }
    groups.get(key)!.count += 1;
  });

  return [...groups.values()].sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, "ja"));
}
