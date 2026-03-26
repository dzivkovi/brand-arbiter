"""Tests for cross-brand SOP collision detection (v1.2.0)."""

import sys
from pathlib import Path

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import run_pipeline
from phase1_crucible import (
    RULE_CATALOG,
    AssessmentOutput,
    CollisionReport,
    ComplianceReport,
    EscalationReason,
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
            "collision_groups": [{"name": "Phantom", "rules": ["MC-PAR-001", "FAKE-001"], "reason": "test"}],
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


# ============================================================================
# Step 4: ComplianceReport brand grouping and collision-aware aggregation
# ============================================================================


def _make_assessment(rule_id: str, result: Result) -> AssessmentOutput:
    """Minimal assessment for testing report aggregation."""
    return AssessmentOutput(
        review_id="test-123",
        rule_id=rule_id,
        asset_id="test-asset",
        timestamp="2026-03-23T00:00:00Z",
        final_result=result,
    )


class TestGroupByBrand:
    """Verify brand-grouped result aggregation."""

    def test_separates_mc_and_bc(self):
        """MC and BC rules go into separate brand groups."""
        results = [
            _make_assessment("MC-PAR-001", Result.FAIL),
            _make_assessment("BC-DOM-001", Result.PASS),
        ]
        grouped = ComplianceReport.group_by_brand(results, RULE_CATALOG)
        assert "mastercard" in grouped
        assert "barclays" in grouped
        assert len(grouped["mastercard"]) == 1
        assert len(grouped["barclays"]) == 1

    def test_empty_list(self):
        """Empty results → empty groups."""
        grouped = ComplianceReport.group_by_brand([], RULE_CATALOG)
        assert grouped == {}

    def test_multiple_mc_rules_same_group(self):
        """Multiple MC rules grouped under mastercard."""
        results = [
            _make_assessment("MC-PAR-001", Result.PASS),
            _make_assessment("MC-CLR-002", Result.PASS),
        ]
        grouped = ComplianceReport.group_by_brand(results, RULE_CATALOG)
        assert len(grouped["mastercard"]) == 2


class TestComplianceReportCollisions:
    """Verify collision-aware worst_case aggregation."""

    def test_collisions_escalate_overall(self):
        """When all rules PASS but collision exists → overall ESCALATED."""
        collision = CollisionReport(
            collision_id="col-test",
            rules_involved=["MC-PAR-001", "BC-DOM-001"],
            brands_involved=["mastercard", "barclays"],
            reason="test",
            mathematical_proof="test",
            result=Result.ESCALATED,
            escalation_reason=EscalationReason.CROSS_BRAND_CONFLICT.value,
        )
        overall = ComplianceReport.worst_case(
            [Result.PASS, Result.PASS],
            collisions=[collision],
        )
        assert overall == Result.ESCALATED

    def test_fail_overrides_collision(self):
        """FAIL still wins over collision ESCALATED (FAIL > ESCALATED)."""
        collision = CollisionReport(
            collision_id="col-test",
            rules_involved=["MC-PAR-001", "BC-DOM-001"],
            brands_involved=["mastercard", "barclays"],
            reason="test",
            mathematical_proof="test",
            result=Result.ESCALATED,
            escalation_reason=EscalationReason.CROSS_BRAND_CONFLICT.value,
        )
        overall = ComplianceReport.worst_case(
            [Result.FAIL, Result.PASS],
            collisions=[collision],
        )
        assert overall == Result.FAIL

    def test_backward_compatible_without_collisions(self):
        """No collisions parameter → original behavior preserved."""
        assert ComplianceReport.worst_case([Result.PASS, Result.PASS]) == Result.PASS
        assert ComplianceReport.worst_case([Result.ESCALATED]) == Result.ESCALATED
        assert ComplianceReport.worst_case([Result.FAIL]) == Result.FAIL

    def test_report_preserves_individual_results(self):
        """Collision doesn't overwrite per-rule results."""
        mc_assessment = _make_assessment("MC-PAR-001", Result.FAIL)
        bc_assessment = _make_assessment("BC-DOM-001", Result.PASS)
        collision = CollisionReport(
            collision_id="col-test",
            rules_involved=["MC-PAR-001", "BC-DOM-001"],
            brands_involved=["mastercard", "barclays"],
            reason="test",
            mathematical_proof="test",
            result=Result.ESCALATED,
            escalation_reason=EscalationReason.CROSS_BRAND_CONFLICT.value,
        )
        report = ComplianceReport(
            asset_id="test",
            timestamp="2026-03-23T00:00:00Z",
            rule_results=[mc_assessment, bc_assessment],
            overall_result=ComplianceReport.worst_case([Result.FAIL, Result.PASS], collisions=[collision]),
            collisions=[collision],
        )
        # Individual results preserved under the collision umbrella
        assert report.rule_results[0].final_result == Result.FAIL  # MC-PAR-001
        assert report.rule_results[1].final_result == Result.PASS  # BC-DOM-001
        assert len(report.collisions) == 1


# ============================================================================
# Step 5: Pipeline integration — collision detection wired into run_pipeline()
# ============================================================================


class TestPipelineCollisionDetection:
    """Verify run_pipeline() detects and reports cross-brand collisions."""

    def test_no_collision_single_brand(self):
        """Default MC-only rules → no collisions."""
        report = run_pipeline(
            "compliant",
            "fake.png",
            dry_run=True,
            rule_ids=["MC-PAR-001", "MC-CLR-002"],
        )
        assert report.collisions == []

    def test_pipeline_has_brand_results(self):
        """run_pipeline populates brand_results grouping."""
        report = run_pipeline(
            "compliant",
            "fake.png",
            dry_run=True,
            rule_ids=["MC-PAR-001", "MC-CLR-002"],
        )
        assert "mastercard" in report.brand_results
        assert len(report.brand_results["mastercard"]) == 2

    def test_cobrand_detects_collision(self):
        """barclays_cobrand with both brands → collision detected."""
        report = run_pipeline(
            "barclays_cobrand",
            "fake.png",
            dry_run=True,
            rule_ids=["MC-PAR-001", "MC-CLR-002", "BC-DOM-001"],
        )
        assert len(report.collisions) == 1
        assert "MC-PAR-001" in report.collisions[0].rules_involved
        assert "BC-DOM-001" in report.collisions[0].rules_involved

    def test_cobrand_preserves_individual_results(self):
        """Collision doesn't mask per-rule verdicts."""
        report = run_pipeline(
            "barclays_cobrand",
            "fake.png",
            dry_run=True,
            rule_ids=["MC-PAR-001", "BC-DOM-001"],
        )
        mc_par = next(a for a in report.rule_results if a.rule_id == "MC-PAR-001")
        bc_dom = next(a for a in report.rule_results if a.rule_id == "BC-DOM-001")
        # MC fails parity (area_ratio 0.833 < 0.95)
        assert mc_par.final_result == Result.FAIL
        # BC passes dominance (ratio 1.20 >= 1.20)
        assert bc_dom.final_result == Result.PASS

    def test_cobrand_brand_grouping(self):
        """Cobrand report groups by mastercard and barclays."""
        report = run_pipeline(
            "barclays_cobrand",
            "fake.png",
            dry_run=True,
            rule_ids=["MC-PAR-001", "BC-DOM-001"],
        )
        assert "mastercard" in report.brand_results
        assert "barclays" in report.brand_results
