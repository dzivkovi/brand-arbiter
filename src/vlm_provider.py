"""
VLM Provider Abstraction (TODO-011)
====================================
Minimal provider interface for swapping between VLM backends.

Each provider is a transport layer: image + prompt in, raw text out.
Domain validation stays in `parse_track_b_response()` (the parsing firewall).

The `schema` parameter is a forward-compatible hook for TODO-014
(structured outputs). Implementations ignore it until then.

Author: Daniel Zivkovic, Magma Inc.
Date: March 27, 2026
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Protocol

import anthropic
from google import genai
from PIL import Image

# ============================================================================
# Provider-agnostic exception (C4 fix — no SDK-specific leaks)
# ============================================================================


class VLMError(Exception):
    """Raised when a VLM provider call fails.

    Wraps SDK-specific exceptions (anthropic.APIError, Google SDK errors)
    so the pipeline catches one type, not N provider-specific types.
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause


# ============================================================================
# Provider Protocol
# ============================================================================


class VLMProvider(Protocol):
    """Minimal interface for VLM backends.

    Implementations MUST:
    - Return raw text from the VLM (caller parses with parse_track_b_response)
    - Raise VLMError on any API/network failure
    - Expose model_version for audit trail
    """

    @property
    def model_version(self) -> str: ...

    def analyze(self, image_path: str | Path, prompt: str, schema: dict | None = None) -> str: ...


# ============================================================================
# Image encoding (private — avoids circular import with live_track_b.py)
# ============================================================================

_MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def _encode_image_base64(image_path: str | Path) -> tuple[str, str]:
    """Encode an image file to base64, returning (data, media_type)."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    media_type = _MEDIA_TYPES.get(path.suffix.lower(), "image/png")
    return data, media_type


# ============================================================================
# Claude Provider
# ============================================================================


class ClaudeProvider:
    """Anthropic Claude Vision API provider.

    Extracted from live_track_b.call_live_track_b().
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key

    @property
    def model_version(self) -> str:
        return self._model

    def analyze(self, image_path: str | Path, prompt: str, schema: dict | None = None) -> str:
        """Send image + prompt to Claude, return raw response text.

        schema is accepted for forward compatibility (TODO-014) but ignored.
        """
        try:
            client = anthropic.Anthropic(api_key=self._api_key) if self._api_key else anthropic.Anthropic()
            image_data, media_type = _encode_image_base64(image_path)

            response = client.messages.create(
                model=self._model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            return response.content[0].text.strip()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise VLMError(f"Claude API call failed: {e}", cause=e) from e


# ============================================================================
# Gemini Provider
# ============================================================================


class GeminiProvider:
    """Google Gemini Vision API provider.

    Uses google-genai SDK with PIL image input.
    Auto-detects GOOGLE_API_KEY or GEMINI_API_KEY from env when no api_key is passed.
    """

    def __init__(
        self,
        model: str = "gemini-3-flash-preview",
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key

    @property
    def model_version(self) -> str:
        return self._model

    def analyze(self, image_path: str | Path, prompt: str, schema: dict | None = None) -> str:
        """Send image + prompt to Gemini, return raw response text.

        schema is accepted for forward compatibility (TODO-014) but ignored.
        """
        try:
            client = genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
            with Image.open(image_path) as image:
                response = client.models.generate_content(
                    model=self._model,
                    contents=[image, prompt],
                )
            return response.text.strip()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise VLMError(f"Gemini API call failed: {e}", cause=e) from e


# ============================================================================
# Provider Factory
# ============================================================================

_PROVIDERS: dict[str, type] = {
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
}


def get_provider(name: str, **kwargs) -> ClaudeProvider | GeminiProvider:
    """Resolve a provider by name.

    Raises ValueError with available providers if name is unknown.
    """
    cls = _PROVIDERS.get(name)
    if cls is None:
        available = sorted(_PROVIDERS.keys())
        raise ValueError(f"Unknown provider: {name!r}. Available: {available}")
    return cls(**kwargs)
