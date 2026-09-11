"""End-to-end smoke test. Run: python -m tests.smoke"""

import asyncio
import json

import httpx

from backend.config import get_settings
from backend.main import app

S = get_settings()
AUTH = {"Authorization": f"Bearer {S.demo_key}"}


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            # 1. auth is enforced
            r = await c.get("/v1/models")
            assert r.status_code == 401, r.status_code
            print("auth rejects unkeyed requests ..... ok")

            # 2. model listing
            r = await c.get("/v1/models", headers=AUTH)
            assert r.json()["data"][0]["id"] == S.agent_model_id
            print("GET /v1/models .................... ok")

            # 3. schema discovery
            schema = (await c.get("/v1/agent/schema", headers=AUTH)).json()
            print(f"schema ............................ {len(schema['tables'])} tables, "
                  f"{len(schema['measures'])} measures")

            # 4. read-only guard
            r = await c.post("/v1/agent/dax", headers=AUTH, json={"dax": "DROP TABLE Sales"})
            assert r.status_code == 400
            print("write statements blocked .......... ok")

            # 5. direct DAX
            r = await c.post("/v1/agent/dax", headers=AUTH, json={
                "dax": 'EVALUATE SUMMARIZECOLUMNS ( Product[Category], "Total Sales", [Total Sales] )'
            })
            body = r.json()
            print(f"POST /v1/agent/dax ................ {body['rowCount']} rows, "
                  f"cols={body['columns']}")

            # 6. non-streaming completion
            r = await c.post("/v1/chat/completions", headers=AUTH, json={
                "model": S.agent_model_id,
                "messages": [{"role": "user", "content": "Top 3 countries by margin in 2024"}],
            }, timeout=60)
            payload = r.json()
            assert payload["object"] == "chat.completion"
            print("POST /v1/chat/completions ......... ok")
            print("-" * 62)
            print(payload["choices"][0]["message"]["content"])
            print("-" * 62)
            dax_step = next(s for s in payload["fabric_agent"]["steps"] if s.get("tool") == "dax")
            print("DAX the agent wrote:")
            print(dax_step["dax"])
            print("-" * 62)

            # 7. streaming
            chunks, steps = [], 0
            async with c.stream("POST", "/v1/chat/completions", headers=AUTH, json={
                "model": S.agent_model_id,
                "messages": [{"role": "user", "content": "sales by channel"}],
                "stream": True,
            }, timeout=60) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: ") or "[DONE]" in line:
                        continue
                    frame = json.loads(line[6:])
                    # every frame must be a valid chat.completion.chunk
                    assert frame["object"] == "chat.completion.chunk"
                    assert "choices" in frame and "delta" in frame["choices"][0]
                    if "fabric_agent" in frame:
                        steps += 1
                    d = frame["choices"][0]["delta"].get("content")
                    if d:
                        chunks.append(d)
            print(f"streaming ......................... {len(chunks)} deltas, {steps} tool events")
            assert chunks

    print("\nAll checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
