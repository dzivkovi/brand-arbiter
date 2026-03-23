"""Tests for cross-brand SOP collision detection (v1.2.0)."""

import sys
from pathlib import Path

import pytest

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phase1_crucible import (
    RULE_CATALOG,
    _load_yaml,
)


# ============================================================================
# Step 1: YAML schema — BC-DOM-001 and collision_groups
# ============================================================================


class TestYamlSchema:
    """Verify rules.yaml includes Barclays rule and collision groups."""

    def test_catalog_includes_barclays_rule(self):
        """BC-DOM-001 is loaded from rules.yaml."""
        assert "BC-DOM-001" in RULE_CATALOG

    def test_barclays_rule_has_brand_field(self):
        """BC-DOM-001 declares brand: barclays."""
        assert RULE_CATALOG["BC-DOM-001"]["brand"] == "barclays"

    def test_mc_rules_have_brand_field(self):
        """Existing MC rules have brand: mastercard."""
        assert RULE_CATALOG["MC-PAR-001"]["brand"] == "mastercard"
        assert RULE_CATALOG["MC-CLR-002"]["brand"] == "mastercard"

    def test_barclays_rule_has_subject_reference(self):
        """BC-DOM-001 deterministic_spec has subject and reference fields."""
        spec = RULE_CATALOG["BC-DOM-001"]["deterministic_spec"]
        assert spec["subject"] == "barclays"
        assert spec["reference"] == "mastercard"
        assert spec["metric"] == "brand_dominance_ratio"
        assert spec["threshold"] == 1.20

    def test_collision_groups_loaded(self):
        """collision_groups top-level key exists in raw YAML."""
        raw = _load_yaml()
        assert "collision_groups" in raw
        groups = raw["collision_groups"]
        assert len(groups) >= 1
        assert groups[0]["name"] == "Parity vs Dominance"
        assert "MC-PAR-001" in groups[0]["rules"]
        assert "BC-DOM-001" in groups[0]["rules"]
