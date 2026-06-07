import { getPlaces } from "@/lib/checkins";

export async function GET() {
  return new Response(`${JSON.stringify(getPlaces())}\n`, {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}
