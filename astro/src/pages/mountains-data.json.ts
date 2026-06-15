import { getMountainsByLatestVisit, summarizeMountains } from "@/lib/mountains";

export async function GET() {
  const mountains = getMountainsByLatestVisit();
  const stats = summarizeMountains(mountains);

  return new Response(
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        stats: {
          count: stats.count,
          visits: stats.visits,
          highest: stats.highest
            ? {
                name: stats.highest.name,
                elevation: stats.highest.elevation,
              }
            : null,
          latest: stats.latest
            ? {
                name: stats.latest.name,
                last_visit: stats.latest.last_visit,
              }
            : null,
        },
        mountains,
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
