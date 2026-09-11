import "server-only";

/**
 * Server-side access to the agent backend.
 *
 * The API key never reaches the browser. Route handlers call these helpers,
 * which attach the key here on the server. In local development the key can be
 * left unset and it is fetched once from the backend's /demo/key endpoint.
 */

const BASE = (process.env.AGENT_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

let cachedKey: string | null = null;
let inFlight: Promise<string> | null = null;

export async function agentKey(): Promise<string> {
  if (process.env.AGENT_API_KEY) return process.env.AGENT_API_KEY;
  if (cachedKey) return cachedKey;
  if (inFlight) return inFlight;

  inFlight = (async () => {
    const res = await fetch(`${BASE}/demo/key`, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(
        "No AGENT_API_KEY is set and the backend's demo key endpoint is unavailable. " +
          "Set AGENT_API_KEY in .env.local.",
      );
    }
    const body = (await res.json()) as { api_key: string };
    cachedKey = body.api_key;
    return cachedKey;
  })();

  try {
    return await inFlight;
  } finally {
    inFlight = null;
  }
}

export async function agentFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const key = await agentKey();
  return fetch(`${BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${key}`,
      ...(init.headers ?? {}),
    },
  });
}

export function agentBaseUrl(): string {
  return BASE;
}
