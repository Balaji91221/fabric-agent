import { agentFetch } from "@/lib/agent-server";

export const dynamic = "force-dynamic";
// Node runtime so the upstream SSE body streams through untouched instead of
// being buffered by the edge runtime.
export const runtime = "nodejs";

export async function POST(request: Request) {
  const body = await request.json();

  let upstream: Response;
  try {
    upstream = await agentFetch("/v1/chat/completions", {
      method: "POST",
      body: JSON.stringify({ ...body, stream: true }),
    });
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "The agent backend is unreachable." },
      { status: 502 },
    );
  }

  if (!upstream.ok || !upstream.body) {
    return Response.json({ error: (await upstream.text()).slice(0, 500) }, { status: upstream.status });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
