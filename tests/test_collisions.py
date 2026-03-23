"""Tests for cross-brand SOP collision detection (v1.2.0)."""

import sys
from pathlib import Path

import pytest

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phase1_crucible import (
    CollisionReport,
    EscalationReason,
    RULE_CATALOG,
    Result,
    _load_yaml,
    detect_collisions,
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


# ============================================================================
# Step 2: detect_collisions() — static threshold analysis
# ============================================================================


class TestDetectCollisions:
    """Verify detect_collisions() finds mutually exclusive rule pairs."""

    def test_finds_parity_dominance_conflict(self):
        """MC-PAR-001 vs BC-DOM-001 are detected as conflicting."""
        raw = _load_yaml()
        collisions = detect_collisions(raw)
        assert len(collisions) == 1
        assert "MC-PAR-001" in collisions[0].rules_involved
        assert "BC-DOM-001" in collisions[0].rules_involved

    def test_returns_escalated(self):
        """Collision result is always ESCALATED."""
        raw = _load_yaml()
        collisions = detect_collisions(raw)
        assert collisions[0].result == Result.ESCALATED

    def test_uses_cross_brand_conflict_reason(self):
        """Escalation reason is CROSS_BRAND_CONFLICT."""
        raw = _load_yaml()
        collisions = detect_collisions(raw)
        assert collisions[0].escalation_reason == EscalationReason.CROSS_BRAND_CONFLICT.value

    def test_proof_contains_thresholds(self):
        """Mathematical proof references both thresholds."""
        raw = _load_yaml()
        collisions = detect_collisions(raw)
        proof = collisions[0].mathematical_proof
        assert "0.95" in proof
        assert "1.2" in proof
        assert "1.0526" in proof  # 1/0.95

    def test_brands_involved(self):
        """Collision report includes both brand namespaces."""
        raw = _load_yaml()
        collisions = detect_collisions(raw)
        assert "mastercard" in collisions[0].brands_involved
        assert "barclays" in collisions[0].brands_involved

    def test_empty_when_no_collision_groups(self):
        """No collisions when collision_groups key is absent."""
        raw = {"rules": {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}}
        collisions = detect_collisions(raw)
        assert collisions == []

    def test_skips_unknown_rule_ids(self):
        """Collision groups referencing nonexistent rules are skipped."""
        raw = {
            "rules": {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]},
            "collision_groups": [
                {"name": "Phantom", "rules": ["MC-PAR-001", "FAKE-001"], "reason": "test"}
            ],
        }
        collisions = detect_collisions(raw)
        assert collisions == []

    def test_respects_active_rules_filter(self):
        """No collision when active_rules excludes one side."""
        raw = _load_yaml()
        collisions = detect_collisions(raw, active_rules=["MC-PAR-001", "MC-CLR-002"])
        assert collisions == []

    def test_active_rules_includes_both_finds_collision(self):
        """Collision detected when active_rules includes both sides."""
        raw = _load_yaml()
        collisions = detect_collisions(raw, active_rules=["MC-PAR-001", "BC-DOM-001"])
        assert len(collisions) == 1
