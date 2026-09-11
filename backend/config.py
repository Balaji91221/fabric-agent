"""Configuration for the Fabric semantic-model agent."""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_KEY_FILE = ROOT / ".demo_key"


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Everything the service needs, read once from the environment."""

    def __init__(self) -> None:
        # --- Agent identity -------------------------------------------------
        # This is the model name clients send in `"model": "..."`.
        self.agent_model_id = os.getenv("AGENT_MODEL_ID", "fabric-semantic-agent")
        self.agent_display_name = os.getenv(
            "AGENT_DISPLAY_NAME", "Fabric Semantic Model Agent"
        )
        self.max_tool_turns = int(os.getenv("AGENT_MAX_TOOL_TURNS", "6"))
        self.max_rows_returned = int(os.getenv("AGENT_MAX_ROWS", "200"))

        # --- Microsoft Fabric / Power BI ------------------------------------
        self.tenant_id = os.getenv("FABRIC_TENANT_ID", "")
        self.client_id = os.getenv("FABRIC_CLIENT_ID", "")
        self.client_secret = os.getenv("FABRIC_CLIENT_SECRET", "")
        self.workspace_id = os.getenv("FABRIC_WORKSPACE_ID", "")
        self.dataset_id = os.getenv("FABRIC_DATASET_ID", "")
        self.powerbi_api_base = os.getenv(
            "FABRIC_API_BASE", "https://api.powerbi.com/v1.0/myorg"
        )
        self.aad_scope = os.getenv(
            "FABRIC_SCOPE", "https://analysis.windows.net/powerbi/api/.default"
        )

        # --- Upstream LLM (any OpenAI-compatible endpoint) ------------------
        self.llm_base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT", "90"))

        # --- Serving --------------------------------------------------------
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.cors_origins = [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "*").split(",")
            if o.strip()
        ]

        # --- Keys -----------------------------------------------------------
        # Extra keys for real clients, comma separated.
        self.api_keys = {
            k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()
        }
        self.expose_demo_key = _bool("EXPOSE_DEMO_KEY", True)
        self.demo_key = self._load_or_create_demo_key()
        self.api_keys.add(self.demo_key)

    # ------------------------------------------------------------------ #

    @property
    def fabric_configured(self) -> bool:
        return all(
            [self.tenant_id, self.client_id, self.client_secret, self.dataset_id]
        )

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def mode(self) -> str:
        return "live" if self.fabric_configured else "demo"

    def _load_or_create_demo_key(self) -> str:
        env_key = os.getenv("DEMO_API_KEY", "").strip()
        if env_key:
            return env_key
        if DEMO_KEY_FILE.exists():
            existing = DEMO_KEY_FILE.read_text(encoding="utf-8").strip()
            if existing:
                return existing
        key = "sk-fabric-demo-" + secrets.token_urlsafe(24)
        try:
            DEMO_KEY_FILE.write_text(key + "\n", encoding="utf-8")
            DEMO_KEY_FILE.chmod(0o600)
        except OSError:
            pass
        return key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
