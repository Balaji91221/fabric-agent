import type { AgentStep, ChatMessage } from "./types";

interface StreamHandlers {
  onStep: (step: AgentStep) => void;
  onDelta: (text: string) => void;
}

/**
 * Reads the agent's SSE stream. The backend is OpenAI-compatible, so every
 * frame is a valid `chat.completion.chunk`; tool activity rides along on an
 * extra `fabric_agent` key that standard clients ignore.
 */
export async function streamChat(
  messages: ChatMessage[],
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<string> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = `Request failed with status ${res.status}.`;
    try {
      const body = await res.json();
      if (body?.error) detail = String(body.error);
    } catch {
      /* keep the status-based message */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let answer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const payload = line.slice(5).trim();
      if (!payload || payload === "[DONE]") continue;

      let chunk: any;
      try {
        chunk = JSON.parse(payload);
      } catch {
        continue;
      }

      if (chunk.fabric_agent) handlers.onStep(chunk.fabric_agent as AgentStep);

      const delta: string | undefined = chunk.choices?.[0]?.delta?.content;
      if (delta) {
        answer += delta;
        handlers.onDelta(answer);
      }
    }
  }

  return answer;
}
