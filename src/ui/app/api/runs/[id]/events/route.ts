const updates = [
  ["lit", "complete"],
  ["patent", "complete"],
  ["trial", "complete"],
  ["mr", "complete"],
  ["lbd", "complete"],
  ["contradiction", "complete"],
  ["ranker", "complete"],
  ["structure", "complete"],
  ["generator", "complete"],
  ["validator", "complete"],
  ["perturbation", "complete"],
  ["report", "complete"]
];

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = updates
    .map(([agent, status]) => `event: agent\ndata: ${JSON.stringify({ id, agent, status })}\n\n`)
    .join("");
  return new Response(body, {
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache"
    }
  });
}
