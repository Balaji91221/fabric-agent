import { NextResponse } from "next/server";
import { agentFetch } from "@/lib/agent-server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const refresh = new URL(request.url).searchParams.get("refresh") === "true";
  try {
    const res = await agentFetch(`/v1/agent/schema?refresh=${refresh}`);
    if (!res.ok) {
      return NextResponse.json({ error: (await res.text()).slice(0, 500) }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "The agent backend is unreachable." },
      { status: 502 },
    );
  }
}
