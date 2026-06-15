import visitedMountains from "../../data/visited_mountains.json";

export type MountainActivity = {
  id: number;
  name: string;
  date: string;
  sport_type: string;
  distance_km: number;
};

export type RawMountain = {
  name: string;
  lat: number;
  lng: number;
  elevation: number;
  tags?: string[];
  visit_count?: number;
  activities?: MountainActivity[];
  first_visit?: string;
  last_visit?: string;
};

export type Mountain = {
  name: string;
  lat: number;
  lng: number;
  elevation: number;
  tags: string[];
  visit_count: number;
  activities: MountainActivity[];
  first_visit: string;
  last_visit: string;
};

export function getMountains(): Mountain[] {
  return (visitedMountains as RawMountain[]).map((mountain) => ({
    name: mountain.name,
    lat: mountain.lat,
    lng: mountain.lng,
    elevation: mountain.elevation,
    tags: mountain.tags || [],
    visit_count: mountain.visit_count || 0,
    activities: mountain.activities || [],
    first_visit: mountain.first_visit || "",
    last_visit: mountain.last_visit || "",
  }));
}

export function getMountainsByElevation(): Mountain[] {
  return [...getMountains()].sort((a, b) => b.elevation - a.elevation);
}

export function getMountainsByLatestVisit(): Mountain[] {
  return [...getMountains()].sort((a, b) => {
    const dateCompare = b.last_visit.localeCompare(a.last_visit);
    if (dateCompare !== 0) return dateCompare;

    return b.elevation - a.elevation;
  });
}

export function summarizeMountains(mountains: Mountain[]) {
  const highest = mountains.reduce<Mountain | null>(
    (current, mountain) => (!current || mountain.elevation > current.elevation ? mountain : current),
    null,
  );
  const latest = mountains.reduce<Mountain | null>(
    (current, mountain) => (!current || mountain.last_visit > current.last_visit ? mountain : current),
    null,
  );

  return {
    count: mountains.length,
    visits: mountains.reduce((sum, mountain) => sum + mountain.visit_count, 0),
    highest,
    latest,
  };
}

export function latestMountainActivity(mountain: Mountain) {
  return mountain.activities.reduce<MountainActivity | null>(
    (current, activity) => (!current || activity.date > current.date ? activity : current),
    null,
  );
}
