# Fabric Semantic Model Agent

An agent that answers questions about **one Microsoft Fabric semantic model** by writing DAX, running it, and explaining the result. It is exposed as an **OpenAI-compatible API**, so any OpenAI client can talk to it by changing `base_url` — the agent is the model.

[Quick start](#run-it) · [Client example](#use-it-as-an-openai-model) · [Architecture](#architecture) · [Configuration](#connect-a-real-semantic-model)

## Why this exists

A business question should lead to an inspectable query and result, not just an answer with unexplained numbers. This project puts schema discovery, DAX execution, and the explanation in one workflow. It is useful for engineers prototyping conversational access to a semantic model and analysts evaluating the evidence behind an answer.

## Architecture

```
frontend-next/   Next.js console (App Router, TypeScript, Tailwind)
      │  POST /api/chat  ── key attached server-side, never in the browser
      ▼
backend/         FastAPI, OpenAI-compatible
      │  agent loop: get_model_schema -> run_dax_query -> answer
      ▼
Microsoft Fabric POST /datasets/{id}/executeQueries    (read-only DAX)
```

## Run it

Use Python 3.10+ and Node.js with npm for the console. The Bash scripts create a Python virtual environment and install the declared dependencies.

```bash
cp .env.example .env                  # optional — it runs without one
cp frontend-next/.env.local.example frontend-next/.env.local
./dev.sh                              # backend on :8000, console on :3000
```

Open <http://localhost:3000>. To run only the backend (it serves a small
dependency-free page at `/` as a fallback), use `./run.sh` and open
<http://localhost:8000>.

The demo key is printed at startup and written to `.demo_key`:

```
  mode            demo
  agent / model   fabric-semantic-agent
  demo key        sk-fabric-demo-XXXXXXXXXXXXXXXXXXXXXXXX
  base_url        http://localhost:8000/v1
```

With no configuration it starts in **demo mode**: a built-in Contoso-style semantic model (4 tables, 8 measures, two years of data) and a deterministic query planner. Everything is exercisable before you connect anything real.

## Use it as an OpenAI model

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-fabric-demo-...")

r = client.chat.completions.create(
    model="fabric-semantic-agent",
    messages=[{"role": "user", "content": "Top 5 countries by margin in 2024"}],
)
print(r.choices[0].message.content)
```

Streaming, `client.models.list()`, and `AuthenticationError` on a bad key all behave the way the SDK expects. Tool activity rides along as a `fabric_agent` key on otherwise-valid chunks, which strict clients ignore and the bundled frontend uses to render the DAX and result grid.

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $(cat .demo_key)" \
  -H 'Content-Type: application/json' \
  -d '{"model":"fabric-semantic-agent","messages":[{"role":"user","content":"sales by channel"}]}'
```

## The console

`frontend-next/` is a Next.js App Router app in TypeScript with Tailwind. Three things are worth knowing about how it is put together:

**The API key stays on the server.** The browser never receives it. `app/api/chat`, `app/api/schema` and `app/api/info` are route handlers that attach the key in `lib/agent-server.ts` and proxy to the backend; the chat route passes the SSE body straight through so streaming still works. In development the key is pulled once from `/demo/key`; in production set `AGENT_API_KEY` in `frontend-next/.env.local` and run the backend with `EXPOSE_DEMO_KEY=false`.

**The schema is server-rendered.** `app/page.tsx` fetches the model and agent metadata before first paint, so the explorer is populated immediately instead of after a client round trip.

**Every answer keeps its provenance.** Each turn renders the DAX the agent wrote, the result grid, then the prose — in that order, on screen together. The last numeric column carries a magnitude rule beneath each figure so the shape of the result reads before the numbers do.

Layout is a dark instrument shell (rail, status bar) around a bright result sheet. It collapses to a single column with a drawer under 1024px.

## Connect a real semantic model

Fill in `.env`:

```env
FABRIC_TENANT_ID=...
FABRIC_CLIENT_ID=...
FABRIC_CLIENT_SECRET=...
FABRIC_WORKSPACE_ID=...
FABRIC_DATASET_ID=...
```

On the Fabric side you need three things:

1. An Entra ID app registration (client credentials).
2. A security group containing that service principal, allowed under **Tenant settings → Developer settings → Service principals can use Fabric APIs**, and **Dataset Execute Queries REST API** enabled.
3. The service principal added to the workspace with at least **Contributor**, plus **Build** permission on the semantic model.

Schema discovery uses the DAX `INFO.TABLES()` / `INFO.COLUMNS()` / `INFO.MEASURES()` / `INFO.RELATIONSHIPS()` functions through the same `executeQueries` endpoint, so no XMLA endpoint or Premium capacity gateway setup is required.

## Give the agent a real reasoning model

Without `LLM_API_KEY` the agent uses a built-in planner that handles grouped aggregation, top-N, year filters and measure selection. Set a key to get the full tool-calling loop, which handles multi-step questions and recovers from DAX errors:

```env
LLM_BASE_URL=https://api.openai.com/v1     # or Azure OpenAI, or a local server
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/chat/completions` | Ask the agent. Streaming and non-streaming. |
| GET | `/v1/models` | Lists the agent as a model. |
| GET | `/v1/agent/info` | Mode, dataset, reasoning model. |
| GET | `/v1/agent/schema` | Tables, columns, measures, relationships. |
| POST | `/v1/agent/dax` | Run DAX directly, bypassing the agent. |
| GET | `/demo/key` | Hands the browser demo its key. |
| GET | `/healthz` | Liveness. |

## Keys

A demo key is generated on first boot, saved to `.demo_key` (mode 600), and served at `/demo/key` so the bundled frontend works with no setup. Before you put this anywhere shared:

```env
EXPOSE_DEMO_KEY=false
API_KEYS=sk-live-key-one,sk-live-key-two
CORS_ORIGINS=https://your-app.example.com
```

## Safety

Queries must start with `EVALUATE` or `DEFINE`, and `ALTER / CREATE / DROP / INSERT / UPDATE / DELETE / REFRESH / EXECUTE` are rejected before anything leaves the process. Fabric would refuse writes anyway; failing early keeps a malformed query from ever reaching the model. Result sets are capped at `AGENT_MAX_ROWS` and the agent loop at `AGENT_MAX_TOOL_TURNS`.

The service principal's own permissions are the real boundary — grant it read access to exactly the model you want exposed and nothing else. Row-level security defined on the semantic model is **not** applied to a service principal identity, so treat this endpoint as having full access to every row in the model.

## Layout

```
backend/          FastAPI app, agent loop, Fabric client, demo model
frontend-next/    Next.js console
  app/api/        route handlers that hold the key server-side
  components/     explorer, transcript, DAX block, result grid, composer
  lib/            stream reader, formatting, DAX tokenizer, types
frontend/         dependency-free fallback page served by the backend at /
tests/smoke.py    end-to-end checks
```

## Tests

```bash
python -m tests.smoke          # backend
cd frontend-next && npm run build   # types + production build
```

The smoke test covers auth rejection, model listing, schema discovery, the read-only guard, direct DAX, and both completion modes.
