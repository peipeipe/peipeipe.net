import stravaActivities from "../../data/strava_activities.json";

export type ActivityKind = "run" | "ride" | "walk" | "swim" | "other";

export type RawActivity = {
  id: number;
  name: string;
  sport_type?: string;
  distance?: number;
  moving_time?: number;
  total_elevation_gain?: number;
  start_date?: string;
  summary_polyline?: string;
};

export type Activity = {
  id: number;
  name: string;
  sport_type: string;
  type_class: ActivityKind;
  distance: number;
  moving_time: number;
  total_elevation_gain: number;
  start_date: string;
  summary_polyline: string | null;
};

export function getActivities(): Activity[] {
  return (stravaActivities as RawActivity[]).map((activity) => ({
    id: activity.id,
    name: activity.name,
    sport_type: activity.sport_type || "",
    type_class: activityType(activity),
    distance: activity.distance || 0,
    moving_time: activity.moving_time || 0,
    total_elevation_gain: activity.total_elevation_gain || 0,
    start_date: activity.start_date || "",
    summary_polyline: activity.summary_polyline || null,
  }));
}

export function activityType(activity: RawActivity): ActivityKind {
  const sport = (activity.sport_type || "").toLowerCase();
  if (sport.includes("run") || sport.includes("trail")) return "run";
  if (sport.includes("ride") || sport.includes("cycling")) return "ride";
  if (sport.includes("walk") || sport.includes("hike")) return "walk";
  if (sport.includes("swim")) return "swim";
  return "other";
}

export function summarizeActivities(activities: Activity[]) {
  return activities.reduce(
    (sum, activity) => ({
      count: sum.count + 1,
      distance: sum.distance + activity.distance,
      moving_time: sum.moving_time + activity.moving_time,
      elevation: sum.elevation + activity.total_elevation_gain,
    }),
    { count: 0, distance: 0, moving_time: 0, elevation: 0 },
  );
}

export function formatDate(date?: string) {
  if (!date) return "";
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(date));
}

export function formatDistance(meters = 0) {
  return `${(meters / 1000).toFixed(1)} km`;
}

export function formatDuration(seconds = 0) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours > 0 ? `${hours}h${minutes}m` : `${minutes}m`;
}
