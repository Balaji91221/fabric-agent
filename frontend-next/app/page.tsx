import Console from "@/components/Console";
import { agentFetch } from "@/lib/agent-server";
import type { AgentInfo, ModelSchema } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * The schema and agent metadata are fetched on the server, so the explorer is
 * populated on first paint rather than after a client round trip.
 */
async function load(): Promise<{
  info: AgentInfo | null;
  schema: ModelSchema | null;
  error: string | null;
}> {
  try {
    const [infoRes, schemaRes] = await Promise.all([
      agentFetch("/v1/agent/info"),
      agentFetch("/v1/agent/schema"),
    ]);

    if (!infoRes.ok || !schemaRes.ok) {
      return { info: null, schema: null, error: "The agent backend returned an error." };
    }

    return {
      info: (await infoRes.json()) as AgentInfo,
      schema: (await schemaRes.json()) as ModelSchema,
      error: null,
    };
  } catch (err) {
    return {
      info: null,
      schema: null,
      error:
        err instanceof Error
          ? err.message
          : "The agent backend is unreachable. Start it, then reload.",
    };
  }
}

export default async function Page() {
  const { info, schema, error } = await load();
  return <Console info={info} schema={schema} bootError={error} />;
}
