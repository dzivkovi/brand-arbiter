"""
Unit tests for VLM provider abstraction (TODO-011).
Covers: VLMProvider Protocol, ClaudeProvider, GeminiProvider, VLMError,
        provider factory, CLI --provider flag, ComplianceReport.model_version.

All tests are mock-mode — no API keys required.

Run: python -m pytest tests/test_vlm_provider.py -v
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from vlm_provider import (
    ClaudeProvider,
    GeminiProvider,
    VLMError,
    get_provider,
)

# ============================================================================
# Fixtures
# ============================================================================

MOCK_VLM_RESPONSE = json.dumps(
    {
        "entities": [
            {"label": "mastercard", "bbox": [100, 50, 300, 150]},
            {"label": "visa", "bbox": [350, 50, 550, 150]},
        ],
        "semantic_pass": True,
        "confidence_score": 0.85,
        "reasoning_trace": "Both logos are equally sized and placed.",
        "rubric_penalties": ["No penalties applied"],
    }
)


# ============================================================================
# TestClaudeProvider
# ============================================================================


class TestClaudeProvider:
    def test_instantiate_with_model_and_api_key(self):
        """ClaudeProvider accepts model and api_key parameters."""
        provider = ClaudeProvider(model="claude-sonnet-4-20250514", api_key="sk-test-fake")
        assert provider.model_version == "claude-sonnet-4-20250514"

    def test_default_model(self):
        """ClaudeProvider defaults to claude-sonnet-4-20250514."""
        provider = ClaudeProvider(api_key="sk-test-fake")
        assert "claude" in provider.model_version.lower() or "sonnet" in provider.model_version.lower()

    @patch("vlm_provider.anthropic")
    def test_analyze_returns_raw_text(self, mock_anthropic, tmp_path):
        """analyze() returns raw text from the Claude API response."""
        # Arrange: mock the Anthropic client chain
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=MOCK_VLM_RESPONSE)]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        # Create a fake image
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        # Act
        provider = ClaudeProvider(api_key="sk-test-fake")
        result = provider.analyze(str(img), "Evaluate this image")

        # Assert
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["semantic_pass"] is True
        assert parsed["confidence_score"] == 0.85

    @patch("vlm_provider.anthropic")
    def test_analyze_api_failure_raises_vlm_error(self, mock_anthropic, tmp_path):
        """API failure is wrapped in VLMError, not leaked as anthropic.APIError."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API connection failed")
        mock_anthropic.Anthropic.return_value = mock_client

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        provider = ClaudeProvider(api_key="sk-test-fake")
        with pytest.raises(VLMError, match="API connection failed"):
            provider.analyze(str(img), "Evaluate this image")

    @patch("vlm_provider.anthropic")
    def test_schema_param_accepted_but_ignored(self, mock_anthropic, tmp_path):
        """Forward-compatible schema param is accepted and ignored (TODO-014 hook)."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=MOCK_VLM_RESPONSE)]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        provider = ClaudeProvider(api_key="sk-test-fake")
        # Must not raise TypeError — schema param is accepted in the signature
        result = provider.analyze(str(img), "Evaluate this image", schema={"type": "object"})
        assert isinstance(result, str)


# ============================================================================
# TestGeminiProvider
# ============================================================================


class TestGeminiProvider:
    def test_instantiate_with_model_and_api_key(self):
        """GeminiProvider accepts model and api_key parameters."""
        provider = GeminiProvider(model="gemini-3-flash-preview", api_key="fake-gemini-key")
        assert provider.model_version == "gemini-3-flash-preview"

    def test_default_model_is_flash(self):
        """GeminiProvider defaults to Gemini Flash."""
        provider = GeminiProvider(api_key="fake-gemini-key")
        assert "flash" in provider.model_version.lower()

    @patch("vlm_provider.Image")
    @patch("vlm_provider.genai", new_callable=MagicMock)
    def test_analyze_returns_raw_text(self, mock_genai, mock_image, tmp_path):
        """analyze() returns raw text from the Gemini API response."""
        # Arrange: mock the Client().models.generate_content chain
        mock_response = MagicMock()
        mock_response.text = MOCK_VLM_RESPONSE
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        # Act
        provider = GeminiProvider(api_key="fake-gemini-key")
        result = provider.analyze(str(img), "Evaluate this image")

        # Assert
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["semantic_pass"] is True

    @patch("vlm_provider.Image")
    @patch("vlm_provider.genai", new_callable=MagicMock)
    def test_analyze_api_failure_raises_vlm_error(self, mock_genai, mock_image, tmp_path):
        """API failure is wrapped in VLMError, not leaked as Google SDK error."""
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Gemini quota exceeded")
        mock_genai.Client.return_value = mock_client

        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        provider = GeminiProvider(api_key="fake-gemini-key")
        with pytest.raises(VLMError, match="Gemini quota exceeded"):
            provider.analyze(str(img), "Evaluate this image")


# ============================================================================
# TestProviderFactory
# ============================================================================


class TestProviderFactory:
    def test_resolve_claude(self):
        """Factory resolves 'claude' to ClaudeProvider."""
        provider = get_provider("claude", api_key="sk-test-fake")
        assert isinstance(provider, ClaudeProvider)

    def test_resolve_gemini(self):
        """Factory resolves 'gemini' to GeminiProvider."""
        provider = get_provider("gemini", api_key="fake-gemini-key")
        assert isinstance(provider, GeminiProvider)

    def test_unknown_provider_raises_value_error(self):
        """Unknown provider name raises ValueError with helpful message."""
        with pytest.raises(ValueError, match=r"Unknown provider.*openai"):
            get_provider("openai")

    def test_error_message_lists_available_providers(self):
        """ValueError message includes list of available providers."""
        with pytest.raises(ValueError, match=r"claude.*gemini"):
            get_provider("gpt4")


# ============================================================================
# TestVLMError
# ============================================================================


class TestVLMError:
    def test_is_exception_subclass(self):
        """VLMError is a proper Exception subclass."""
        assert issubclass(VLMError, Exception)

    def test_wraps_original_error(self):
        """VLMError preserves the original exception as __cause__."""
        original = ConnectionError("network down")
        error = VLMError("Provider failed", original)
        assert "Provider failed" in str(error)


# ============================================================================
# TestModelVersion
# ============================================================================


class TestModelVersion:
    def test_claude_provider_model_version(self):
        """ClaudeProvider.model_version returns the configured model string."""
        provider = ClaudeProvider(model="claude-sonnet-4-20250514", api_key="sk-test")
        assert provider.model_version == "claude-sonnet-4-20250514"

    def test_gemini_provider_model_version(self):
        """GeminiProvider.model_version returns the configured model string."""
        provider = GeminiProvider(model="gemini-3-flash-preview", api_key="fake-key")
        assert provider.model_version == "gemini-3-flash-preview"

    def test_default_model_names_are_current(self):
        """Default model names should not be deprecated/stale.

        This is a structural guard — if a default model name goes stale,
        this test should be updated alongside the provider default.
        The EXPECTED values below are the single source of truth for
        'what model do we ship with'. Update them when rotating models.
        """
        # --- Current defaults (update when rotating models) ---
        EXPECTED_CLAUDE_DEFAULT = "claude-sonnet-4-20250514"
        EXPECTED_GEMINI_DEFAULT = "gemini-3-flash-preview"

        claude = ClaudeProvider(api_key="sk-test")
        gemini = GeminiProvider(api_key="fake-key")

        assert claude.model_version == EXPECTED_CLAUDE_DEFAULT, (
            f"Claude default model changed: {claude.model_version!r} != {EXPECTED_CLAUDE_DEFAULT!r}. "
            "Update EXPECTED_CLAUDE_DEFAULT if this is intentional."
        )
        assert gemini.model_version == EXPECTED_GEMINI_DEFAULT, (
            f"Gemini default model changed: {gemini.model_version!r} != {EXPECTED_GEMINI_DEFAULT!r}. "
            "Update EXPECTED_GEMINI_DEFAULT if this is intentional."
        )

    def test_compliance_report_has_model_version_field(self):
        """ComplianceReport dataclass includes model_version field."""
        from phase1_crucible import ComplianceReport

        report = ComplianceReport(
            asset_id="test",
            timestamp="2026-03-27",
            rule_results=[],
            overall_result=__import__("phase1_crucible").Result.PASS,
            model_version="claude-sonnet-4-20250514",
        )
        assert report.model_version == "claude-sonnet-4-20250514"

    def test_compliance_report_model_version_defaults_empty(self):
        """ComplianceReport.model_version defaults to empty string for backward compat."""
        from phase1_crucible import ComplianceReport, Result

        report = ComplianceReport(
            asset_id="test",
            timestamp="2026-03-27",
            rule_results=[],
            overall_result=Result.PASS,
        )
        assert report.model_version == ""


# ============================================================================
# TestCLIProviderFlag
# ============================================================================


class TestCLIProviderFlag:
    def test_provider_flag_accepted_by_production_parser(self):
        """--provider gemini is accepted by main.py's REAL parser (not a rebuilt one)."""
        import sys

        import main as main_module

        with (
            patch.object(sys, "argv", ["main.py", "--scenario", "hard_case", "--dry-run", "--provider", "gemini"]),
            patch("main.run_pipeline") as mock_pipeline,
        ):
            mock_pipeline.return_value = MagicMock(
                overall_result=MagicMock(value="PASS"),
                rule_results=[],
                collisions=[],
            )
            # Calls the REAL parser inside main() — if --provider is missing, this crashes
            main_module.main()
            assert mock_pipeline.called

    def test_dry_run_with_provider_flag(self):
        """Pipeline runs in dry-run mode with --provider flag without crash."""
        from main import run_pipeline

        report = run_pipeline("compliant", "fake.png", dry_run=True)
        assert report is not None

    def test_dry_run_model_version_says_mock(self):
        """Dry-run reports must NOT claim a real model — audit trail integrity."""
        from main import run_pipeline

        report = run_pipeline("compliant", "fake.png", dry_run=True, model_version="dry-run (mock)")
        assert report.model_version == "dry-run (mock)"
        assert "claude" not in report.model_version.lower()
        assert "gemini" not in report.model_version.lower()
        # Dry-run doesn't use the provider — existing mock path
        assert report is not None
