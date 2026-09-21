import onsenPlaces from "../../data/onsen_places.json";
import places from "../../data/places.json";

export type CheckinPlace = {
  name: string;
  user_comment?: string;
  composition_hint?: string;
  date?: string;
  lat?: number | null;
  lng?: number | null;
  address?: string;
  foursquare_url?: string;
  photos?: string[];
  categories?: string[];
  data_source?: string;
  fsq_id?: string;
  checkin_count?: number;
  first_checkin_at?: string;
  last_checkin_at?: string;
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
