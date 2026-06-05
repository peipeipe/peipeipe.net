import { getActivities, summarizeActivities } from "@/lib/activity";

export async function GET() {
  const activities = getActivities();
  const stats = summarizeActivities(activities);

  return new Response(
    `${JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        stats,
        activities,
      },
      null,
      2,
    )}\n`,
    {
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, max-age=300",
      },
    },
  );
}
