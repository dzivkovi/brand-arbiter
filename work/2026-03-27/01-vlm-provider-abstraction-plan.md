Date: 2026-03-27 at 16:24:20 EDT

# TODO-011: VLM Provider Abstraction — Implementation Plan

## What I'll Build

A minimal provider abstraction that lets Brand Arbiter swap between Claude and Gemini with a CLI flag, while keeping the existing parsing firewall (`parse_track_b_response`) as the single validation point.

## Interface Design

```python
class VLMProvider(Protocol):
    @property
    def model_version(self) -> str: ...
    def analyze(self, image_path: str | Path, prompt: str) -> str: ...
```

The provider is a **transport layer** — it sends image+prompt to the VLM and returns raw text. Domain validation stays in `parse_track_b_response()`.

## Files to Create/Modify

| File | Action | What |
|------|--------|------|
| `src/vlm_provider.py` | **Create** | Protocol + ClaudeProvider + GeminiProvider + factory |
| `src/live_track_b.py` | **Refactor** | `call_live_track_b` delegates to `ClaudeProvider` |
| `src/main.py` | **Modify** | `--provider` CLI flag, inject provider into `run_pipeline`, print `model_version` |
| `tests/test_vlm_provider.py` | **Create** | Mock-mode tests for both providers, factory, CLI flag, model_version |
| `requirements.txt` | **Add** | `google-generativeai>=0.8.0` |
| `pyproject.toml` | **Update** | Add `vlm_provider` to isort known-first-party |

## Key Decisions

1. **Provider returns raw text, not dict** — keeps `parse_track_b_response()` as the single parsing firewall
2. **`model_version` in printed report** — not in dataclass (phase1_crucible.py forbidden)
3. **Gemini Flash as default** (`gemini-2.0-flash`), Claude Sonnet for Claude
4. **Prompt construction stays in caller** — provider just sends what it receives
5. **`google-generativeai`** for Gemini (established, PIL image support)

## Scope Boundaries

Won't touch: `phase1_crucible.py`, `live_track_a.py`, `vlm_perception.py`, `rules.yaml`
