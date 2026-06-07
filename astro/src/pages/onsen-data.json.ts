import { getOnsenPlaces, summarizePlaces } from "@/lib/checkins";

export async function GET() {
  const places = getOnsenPlaces();
  const stats = summarizePlaces(places);

  return new Response(
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        stats: {
          count: stats.count,
          checkins: stats.checkins,
          with_photos: stats.withPhotos,
          latest: stats.latest
            ? {
                name: stats.latest.name,
                date: stats.latest.date,
              }
            : null,
        },
        places,
      },
      null,
      2,
    ),
    {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
      },
    },
  );
}
