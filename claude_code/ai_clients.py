"""
AI client adapters for the insight generation layer.

Each client:
  - Accepts a prompt string
  - Returns a raw text response string
  - Raises a clear, human-readable exception on failure

Supported clients:
  - ClaudeClient  → Anthropic API  (requires: pip install anthropic, ANTHROPIC_API_KEY env var)
  - OllamaClient  → Local Ollama   (requires: ollama running, model pulled)

HOW TO ADD A NEW CLIENT:
  1. Subclass BaseInsightClient
  2. Implement complete()
  3. Register it in CLIENT_REGISTRY at the bottom
"""

import os
from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# Base contract
# ---------------------------------------------------------------------------

class BaseInsightClient(ABC):
    """All AI clients must implement this single method."""

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """
        Send prompt to the LLM and return the raw text response.

        Args:
            prompt: The full prompt string to send.

        Returns:
            Raw text response from the model.

        Raises:
            RuntimeError: On any client/network/auth failure.
        """


# ---------------------------------------------------------------------------
# Claude (Anthropic API)
# ---------------------------------------------------------------------------

DEFAULT_CLAUDE_MODEL = "claude-opus-4-20250514"


class ClaudeClient(BaseInsightClient):
    """
    Calls the Anthropic Claude API.

    Requirements:
        pip install anthropic
        export ANTHROPIC_API_KEY=sk-ant-...

    Args:
        model:   Claude model string (default: claude-opus-4-20250514)
        api_key: API key — falls back to ANTHROPIC_API_KEY env var if omitted.
    """

    def __init__(
        self,
        model: str = DEFAULT_CLAUDE_MODEL,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "Anthropic API key not found. "
                "Set the ANTHROPIC_API_KEY environment variable or pass api_key=."
            )

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise RuntimeError(
                "anthropic package is not installed. Run: pip install anthropic"
            )

    def complete(self, prompt: str) -> str:
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude API call failed: {e}") from e


# ---------------------------------------------------------------------------
# Ollama (local)
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_OLLAMA_HOST  = "http://localhost:11434"


class OllamaClient(BaseInsightClient):
    """
    Calls a locally running Ollama instance.

    Requirements:
        1. Install Ollama: https://ollama.com
        2. Start it:       ollama serve
        3. Pull a model:   ollama pull llama3.2

    Args:
        model: Ollama model name (default: llama3.2)
        host:  Ollama server URL (default: http://localhost:11434)
    """

    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        host: str = DEFAULT_OLLAMA_HOST,
    ) -> None:
        self.model = model
        self.host  = host.rstrip("/")

        try:
            import ollama
            self._ollama = ollama
            self._client = ollama.Client(host=self.host)
        except ImportError:
            raise RuntimeError(
                "ollama package is not installed. Run: pip install ollama"
            )

        self._check_server_reachable()

    def _check_server_reachable(self) -> None:
        """Fail fast with a clear message if Ollama isn't running."""
        try:
            self._client.list()
        except Exception:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.host}. "
                "Make sure Ollama is running: ollama serve"
            )

    def _check_model_available(self) -> None:
        """Warn if the requested model isn't pulled yet."""
        try:
            models = self._client.list()
            names = [m.model for m in models.models]
            # Normalize: "llama3.2:latest" should match "llama3.2"
            normalized = [n.split(":")[0] for n in names]
            if self.model.split(":")[0] not in normalized:
                raise RuntimeError(
                    f"Model '{self.model}' is not available in Ollama. "
                    f"Run: ollama pull {self.model}\n"
                    f"Available models: {', '.join(normalized) or 'none'}"
                )
        except RuntimeError:
            raise
        except Exception:
            pass  # If list() fails for other reasons, let complete() surface the error

    def complete(self, prompt: str) -> str:
        self._check_model_available()
        try:
            response = self._client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.message.content
        except Exception as e:
            raise RuntimeError(f"Ollama completion failed: {e}") from e


# ---------------------------------------------------------------------------
# Registry — maps CLI argument values to client factories
# ---------------------------------------------------------------------------

def get_client(
    client_name: str,
    model: str | None = None,
    **kwargs,
) -> BaseInsightClient:
    """
    Instantiate and return the appropriate AI client by name.

    Args:
        client_name: One of the registered client names (e.g. "claude", "ollama").
        model:       Optional model override. Falls back to each client's default.
        **kwargs:    Passed through to the client constructor (e.g. host= for Ollama).

    Returns:
        A ready-to-use BaseInsightClient instance.

    Raises:
        ValueError:  If client_name is not registered.
        RuntimeError: If the client cannot be initialized (missing package, bad key, etc.)
    """
    name = client_name.lower().strip()

    if name == "claude":
        return ClaudeClient(model=model or DEFAULT_CLAUDE_MODEL, **kwargs)

    if name == "ollama":
        return OllamaClient(model=model or DEFAULT_OLLAMA_MODEL, **kwargs)

    registered = ["claude", "ollama"]
    raise ValueError(
        f"Unknown client '{client_name}'. "
        f"Choose one of: {', '.join(registered)}"
    )


# Expose valid choices for argparse
VALID_CLIENTS = ["claude", "ollama"]
