"""
Cloudflare Workers AI client.

Communicates with the Cloudflare AI REST API to run inference on
edge-deployed models, or (when CLOUDFLARE_WORKER_URL is set) routes
requests through a deployed Cloudflare Python Worker for lower latency.

Cloudflare AI API reference:
  https://developers.cloudflare.com/workers-ai/get-started/rest-api/
"""

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Default text-generation model
DEFAULT_MODEL = "@cf/meta/llama-3.1-8b-instruct"

# Cloudflare AI REST endpoint
_CF_BASE = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/"


class CloudflareAIError(Exception):
    """Raised when the Cloudflare AI API returns an error."""


class CloudflareAIClient:
    """
    Thin wrapper around the Cloudflare Workers AI REST API.

    Usage::

        client = CloudflareAIClient()
        response = client.chat(
            messages=[{"role": "user", "content": "Explain recursion"}]
        )
        print(response)  # "Recursion is when a function calls itself …"
    """

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        worker_url: str | None = None,
        model: str | None = None,
        timeout: int = 30,
    ):
        self.account_id = account_id or settings.CLOUDFLARE_ACCOUNT_ID
        self.api_token = api_token or settings.CLOUDFLARE_API_TOKEN
        self.worker_url = worker_url or getattr(settings, "CLOUDFLARE_WORKER_URL", "")
        self.model = model or getattr(settings, "CLOUDFLARE_AI_MODEL", DEFAULT_MODEL)
        self.timeout = timeout

        self._session = requests.Session()
        if self.api_token:
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                }
            )

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _direct_api_url(self, model: str) -> str:
        return _CF_BASE.format(account_id=self.account_id) + model

    def _run_via_direct_api(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the Cloudflare Workers AI REST API directly."""
        if not self.account_id or not self.api_token:
            raise CloudflareAIError(
                "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be configured."
            )
        url = self._direct_api_url(model)
        try:
            resp = self._session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.Timeout as exc:
            raise CloudflareAIError("Cloudflare AI API request timed out.") from exc
        except requests.RequestException as exc:
            raise CloudflareAIError(f"Cloudflare AI API request failed: {exc}") from exc
        data = resp.json()
        if not data.get("success"):
            errors = data.get("errors", [])
            raise CloudflareAIError(f"Cloudflare AI API errors: {errors}")
        return data.get("result", {})

    def _run_via_worker(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Route the request through the deployed Cloudflare Python Worker."""
        url = self.worker_url.rstrip("/") + path
        try:
            resp = self._session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.Timeout as exc:
            raise CloudflareAIError("Cloudflare Worker request timed out.") from exc
        except requests.RequestException as exc:
            raise CloudflareAIError(f"Cloudflare Worker request failed: {exc}") from exc
        return resp.json()

    def run_model(self, model: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Run an AI model inference.

        If CLOUDFLARE_WORKER_URL is configured the request is forwarded to
        the deployed Python Worker; otherwise the REST API is called directly.
        """
        if self.worker_url:
            logger.debug("Running model %s via worker at %s", model, self.worker_url)
            return self._run_via_worker("/ai/run", {"model": model, **payload})
        logger.debug("Running model %s via direct Cloudflare API", model)
        return self._run_via_direct_api(model, payload)

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        model: str | None = None,
    ) -> str:
        """
        Send a chat messages list to the text-generation model.

        Returns the assistant's text response.
        """
        result = self.run_model(
            model or self.model,
            {"messages": messages, "max_tokens": max_tokens},
        )
        return result.get("response", "")

    def complete(self, prompt: str, max_tokens: int = 1024, model: str | None = None) -> str:
        """Single-turn text completion (wraps the prompt as a user message)."""
        return self.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            model=model,
        )


def get_ai_client() -> CloudflareAIClient:
    """Return a configured :class:`CloudflareAIClient` instance."""
    return CloudflareAIClient()
