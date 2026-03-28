"""
VLM Provider Abstraction (TODO-011, TODO-014)
==============================================
Minimal provider interface for swapping between VLM backends.

Each provider is a transport layer: image + prompt in, raw text out.
Domain validation stays in `parse_track_b_response()` (the parsing firewall).

When a JSON schema is passed, providers use API-level structured outputs
(ADR-0007): Claude via tool-use, Gemini via response_json_schema.

Author: Daniel Zivkovic, Magma Inc.
Date: March 27, 2026
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Protocol

import anthropic
from google import genai
from google.genai import types as genai_types
from PIL import Image

# ============================================================================
# Perception JSON Schema (TODO-014 — single definition, both providers)
# ============================================================================
# Standard JSON Schema matching PerceptionOutput from vlm_perception.py.
# Claude enforces via tool input_schema; Gemini via response_json_schema.
# This is a structural contract — domain validation still lives in the parser.

PERCEPTION_JSON_SCHEMA: dict = {
    "type": "object",
    "required": ["entities", "rule_judgments"],
    "additionalProperties": False,
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label", "bbox", "bbox_confidence", "visibility"],
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "bbox_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "visibility": {"type": "string", "enum": ["full", "partial", "unclear"]},
                },
            },
        },
        "rule_judgments": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["semantic_pass", "confidence_score"],
                "additionalProperties": False,
                "properties": {
                    "semantic_pass": {"type": "boolean"},
                    "confidence_score": {"type": "number", "minimum": 0.10, "maximum": 1.00},
                    "reasoning_trace": {"type": "string"},
                    "rubric_penalties": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "extracted_text": {"type": "string"},
    },
}

# Tool name used by ClaudeProvider for structured output enforcement
_CLAUDE_TOOL_NAME = "perception_output"


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

        When schema is provided, enforces structured output via tool-use:
        defines a tool with input_schema=schema and forces the model to call it.
        The tool's input JSON is returned as the raw text response.
        """
        try:
            client = anthropic.Anthropic(api_key=self._api_key) if self._api_key else anthropic.Anthropic()
            image_data, media_type = _encode_image_base64(image_path)

            messages = [
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
            ]

            if schema is not None:
                # Structured output via tool-use (ADR-0007)
                response = client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    messages=messages,
                    tools=[
                        {
                            "name": _CLAUDE_TOOL_NAME,
                            "description": "Return the brand compliance perception analysis as structured JSON.",
                            "input_schema": schema,
                        }
                    ],
                    tool_choice={"type": "tool", "name": _CLAUDE_TOOL_NAME},
                )
                # Extract the tool-use block's input as JSON text
                for block in response.content:
                    if block.type == "tool_use" and block.name == _CLAUDE_TOOL_NAME:
                        return json.dumps(block.input)
                # Fallback: no tool_use block found — return raw text for parser fallback
                return response.content[0].text.strip() if response.content else ""
            else:
                response = client.messages.create(
                    model=self._model,
                    max_tokens=2000,
                    messages=messages,
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

        When schema is provided, enforces structured output via
        response_json_schema + response_mime_type (ADR-0007).
        """
        try:
            client = genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
            config: dict | genai_types.GenerateContentConfig | None = None
            if schema is not None:
                config = genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=schema,
                )
            with Image.open(image_path) as image:
                response = client.models.generate_content(
                    model=self._model,
                    contents=[image, prompt],
                    config=config,
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
